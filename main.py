import fitz # PyMuPDF
import re
import os
import sys

def extract_sku_locations_from_pdf(pdf_path):
    """
    Extracts all text from a PDF and identifies the locations of SKU codes and their quantities,
    correctly associating them with their Order ID, especially for two-page orders.

    Args:
        pdf_path (str): The path to the PDF file.

    Returns:
        list: A list of dictionaries, each containing 'sku' (text), 'quantity',
              'page_num', 'order_id', and 'bbox' (fitz.Rect).
              Returns None if the file cannot be opened or processed.
    """
    try:
        doc = fitz.open(pdf_path)
        num_pages = doc.page_count
        print(f"Reading {num_pages} page(s) from '{os.path.basename(pdf_path)}' to find SKUs and Quantities...")

        # Regex to find Order ID
        order_id_regex = re.compile(r'Order ID:\s*(\d+)', re.IGNORECASE)
        # Regex to find initial C_ patterns (start of an SKU)
        initial_c_sku_regex = re.compile(r'C[ _][A-Z0-9_/\-\s]+', re.IGNORECASE)
        # Regex to find "xN" multipliers (e.g., x2, X5)
        x_multiplier_regex = re.compile(r'x(\d+)', re.IGNORECASE)
        # Regex to find numbers (potential quantities) - anchored to start/end of word
        quantity_regex = re.compile(r'^\d+$')
        # Regex to find numbers at the end of an SKU part (e.g., '2' in 'BWL2')
        number_at_end_of_sku_part_regex = re.compile(r'(\d+)$')

        # Define search range for quantity/multiplier relative to SKU bbox
        QUANTITY_SEARCH_RANGE_X = 100 # Max horizontal distance to search for quantity (points)
        QUANTITY_SEARCH_RANGE_Y = 40 # Max vertical deviation to consider same line or line below (points)
        X_MULTIPLIER_SEARCH_RANGE_X = 150 # Extended range for 'xN' multiplier search (for external xN/qty)
        X_MULTIPLIER_SAME_LINE_Y_RANGE = 10 # Tighter vertical range for external 'xN' multiplier search
        MAX_WORDS_TO_LOOK_AHEAD_FOR_SKU_NAME = 5 # Max words to combine for multi-word SKU names

        # Define SKU aliases - now used during extraction
        sku_aliases = {
            "WASH-L": "BWL",
            "WASH-M": "BWM",
            "BABY WASH - MILK": "BWM",
            "BABY WASH LAVENDER": "BWL",
            "CBV": "CBV"
        }

        # First pass: Extract all text and find Order IDs per page
        page_order_ids = {}
        for page_num in range(num_pages):
            page = doc.load_page(page_num)
            page_text = page.get_text()
            order_id_match = order_id_regex.search(page_text)
            if order_id_match:
                page_order_ids[page_num] = order_id_match.group(1)
            else:
                page_order_ids[page_num] = "UNKNOWN_ORDER"

        print("\n--- Identified Order IDs per page ---")
        for page_num, order_id in page_order_ids.items():
            print(f"  Page {page_num + 1}: Order ID '{order_id}'")
        print("---------------------------------------")

        sku_locations = []
        for page_num in range(num_pages):
            page = doc.load_page(page_num)
            words = page.get_text("words")
            
            # Get the correct Order ID for the current page
            order_id = page_order_ids[page_num]
            # Handle two-page orders by checking the previous page's Order ID
            if order_id == "UNKNOWN_ORDER" and page_num > 0:
                prev_order_id = page_order_ids[page_num - 1]
                if prev_order_id != "UNKNOWN_ORDER":
                    # Check if previous page had a 'Payment' and current one doesn't,
                    # to confirm it's a two-page order split.
                    if "Payment" in doc.load_page(page_num - 1).get_text() and "Payment" not in page.get_text():
                        order_id = prev_order_id
                        print(f"  Info: Assigning Order ID '{order_id}' from page {page_num} to SKUs on page {page_num + 1}.")

            idx = 0
            while idx < len(words):
                x0, y0, x1, y1, word_text, _, _, _ = words[idx]

                initial_match = initial_c_sku_regex.search(word_text)
                
                if initial_match:
                    current_sku_parts = [word_text.strip()]
                    current_sku_bbox = fitz.Rect(x0, y0, x1, y1)
                    
                    look_ahead_idx = idx + 1
                    while look_ahead_idx < len(words) and \
                          look_ahead_idx < idx + MAX_WORDS_TO_LOOK_AHEAD_FOR_SKU_NAME:
                        
                        next_word_info = words[look_ahead_idx]
                        nox0, noy0, nox1, noy1, next_word_text, _, _, _ = next_word_info

                        if abs(noy0 - y0) <= QUANTITY_SEARCH_RANGE_Y and \
                           (nox0 - x0) < X_MULTIPLIER_SEARCH_RANGE_X + 50 and \
                           not quantity_regex.search(next_word_text.strip()):
                            
                            current_sku_parts.append(next_word_text.strip())
                            current_sku_bbox = current_sku_bbox | fitz.Rect(nox0, noy0, nox1, noy1)
                            look_ahead_idx += 1
                        else:
                            break

                    sku_found_raw = " ".join(current_sku_parts).strip()
                    
                    base_quantity = 1
                    x_multiplier_value = 1

                    temp_sku_string = sku_found_raw
                    x_match_in_sku = x_multiplier_regex.search(temp_sku_string)
                    if x_match_in_sku:
                        try:
                            x_multiplier_value = int(x_match_in_sku.group(1))
                            temp_sku_string = x_multiplier_regex.sub('', temp_sku_string).strip()
                        except ValueError:
                            pass
                    
                    found_base_qty_for_current_sku = False
                    qty_search_start_idx = look_ahead_idx 
                    for j in range(qty_search_start_idx, len(words)):
                        other_word_info = words[j]
                        ox0, oy0, ox1, oy1, other_word_text, _, _, _ = other_word_info

                        if (oy0 >= current_sku_bbox.y0 and abs(oy0 - current_sku_bbox.y0) <= QUANTITY_SEARCH_RANGE_Y and
                            ox0 > current_sku_bbox.x1 and (ox0 - current_sku_bbox.x1) <= QUANTITY_SEARCH_RANGE_X):
                            
                            qty_match = quantity_regex.search(other_word_text.strip())
                            if qty_match:
                                try:
                                    potential_qty = int(qty_match.group(0))
                                    if 0 < potential_qty < 1000:
                                        base_quantity = potential_qty
                                        found_base_qty_for_current_sku = True
                                        break
                                except ValueError:
                                    pass
                        elif (ox0 - current_sku_bbox.x1) > QUANTITY_SEARCH_RANGE_X + 50:
                            break
                    
                    xN_search_start_idx = qty_search_start_idx 
                    for j in range(xN_search_start_idx, len(words)):
                        other_word_info = words[j]
                        ox0, oy0, ox1, oy1, other_word_text, _, _, _ = other_word_info

                        if (oy0 >= current_sku_bbox.y0 and abs(oy0 - current_sku_bbox.y0) <= X_MULTIPLIER_SAME_LINE_Y_RANGE and
                            ox0 > current_sku_bbox.x1 and (ox0 - current_sku_bbox.x1) <= X_MULTIPLIER_SEARCH_RANGE_X):
                            
                            x_match_external = x_multiplier_regex.search(other_word_text.strip())
                            if x_match_external:
                                try:
                                    x_multiplier_value *= int(x_match_external.group(1))
                                    break
                                except ValueError:
                                    pass
                        elif (ox0 - current_sku_bbox.x1) > X_MULTIPLIER_SEARCH_RANGE_X + 50:
                            break
                    
                    initial_combined_quantity = base_quantity * x_multiplier_value
                    processed_sku_string = temp_sku_string
                    if processed_sku_string.startswith("C_"):
                        processed_sku_string = processed_sku_string[2:]
                    elif processed_sku_string.startswith("C "):
                        processed_sku_string = processed_sku_string[2:]
                    
                    processed_sku_string = re.sub(r'\s+', ' ', processed_sku_string).strip()

                    if '/' in processed_sku_string or '+' in processed_sku_string:
                        # Split by both '/' and '+' as separators
                        sub_skus = [s.strip() for s in re.split(r'[/+]', processed_sku_string) if s.strip()]
                        for sub_sku in sub_skus:
                            current_sku_part_quantity = initial_combined_quantity
                            
                            stripped_sub_sku = sub_sku.strip()
                            match_end_number = number_at_end_of_sku_part_regex.search(stripped_sub_sku)
                            if match_end_number:
                                num_at_end_str = match_end_number.group(1)
                                try:
                                    num_at_end_int = int(num_at_end_str)
                                    current_sku_part_quantity *= num_at_end_int
                                    sub_sku = stripped_sub_sku[:-len(num_at_end_str)].strip('_-')
                                except ValueError:
                                    sub_sku = stripped_sub_sku.strip('-')
                            else:
                                sub_sku = stripped_sub_sku.strip('-')

                            if "B1T1" in sub_sku.upper():
                                sub_sku = sub_sku.replace("B1T1", "").replace("b1t1", "").strip('_-')
                                current_sku_part_quantity *= 2

                            normalized_sku_for_lookup = re.sub(r'[\s\-]+', ' ', sub_sku).strip().upper()
                            for original_key, alias_value in sku_aliases.items():
                                if normalized_sku_for_lookup == re.sub(r'[\s\-]+', ' ', original_key).strip().upper():
                                    sub_sku = alias_value
                                    break

                            sku_locations.append({
                                'sku': sub_sku,
                                'quantity': current_sku_part_quantity,
                                'page_num': page_num,
                                'bbox': current_sku_bbox,
                                'order_id': order_id
                            })
                    else:
                        current_sku_quantity = initial_combined_quantity
                        
                        stripped_sku_text = processed_sku_string.strip()
                        match_end_number = number_at_end_of_sku_part_regex.search(stripped_sku_text)
                        if match_end_number:
                            num_at_end_str = match_end_number.group(1)
                            try:
                                num_at_end_int = int(num_at_end_str)
                                current_sku_quantity *= num_at_end_int
                                processed_sku_string = stripped_sku_text[:-len(num_at_end_str)].strip('_-')
                            except ValueError:
                                processed_sku_string = stripped_sku_text.strip('-')
                        else:
                            processed_sku_string = stripped_sku_text.strip('-')

                        if "B1T1" in processed_sku_string.upper():
                            processed_sku_string = processed_sku_string.replace("B1T1", "").replace("b1t1", "").strip('_-')
                            current_sku_quantity *= 2

                        normalized_sku_for_lookup = re.sub(r'[\s\-]+', ' ', processed_sku_string).strip().upper()
                        for original_key, alias_value in sku_aliases.items():
                            if normalized_sku_for_lookup == re.sub(r'[\s\-]+', ' ', original_key).strip().upper():
                                processed_sku_string = alias_value
                                break

                        sku_locations.append({
                            'sku': processed_sku_string,
                            'quantity': current_sku_quantity,
                            'page_num': page_num,
                            'bbox': current_sku_bbox,
                            'order_id': order_id
                        })
                    idx = look_ahead_idx
                else:
                    idx += 1

        doc.close()
    except FileNotFoundError:
        print(f"Error: The file '{pdf_path}' was not found.")
        return None
    except Exception as e:
        print(f"An error occurred while reading the PDF: {e}")
        return None
    return sku_locations

def stamp_skus_on_pdf(input_pdf_path, sku_locations, output_pdf_path, multi_sku_orders_to_stamp):
    """
    Stamps the identified SKU codes and their quantities onto a new PDF document,
    including a summary page at the end.
    """
    try:
        doc = fitz.open(input_pdf_path)
        output_doc = fitz.open()

        font_name = "helv"
        font_size = 12
        MIN_FONT_SIZE = 8

        global_aggregated_skus = {}

        skus_by_page = {}
        for sku_info in sku_locations:
            page_num = sku_info['page_num']
            if page_num not in skus_by_page:
                skus_by_page[page_num] = []
            skus_by_page[page_num].append(sku_info)

        for page_num in range(doc.page_count):
            page = doc.load_page(page_num)
            output_page = output_doc.new_page(
                width=page.rect.width,
                height=page.rect.height
            )
            output_page.show_pdf_page(page.rect, doc, page_num)

            bottom_margin = 20
            left_margin = 20

            page_aggregated_skus = {}

            if page_num in skus_by_page:
                for sku_info in skus_by_page[page_num]:
                    sku_text = sku_info['sku']
                    sku_quantity = sku_info['quantity']

                    if sku_text in page_aggregated_skus:
                        page_aggregated_skus[sku_text] += sku_quantity
                    else:
                        page_aggregated_skus[sku_text] = sku_quantity
                    
                    if sku_text in global_aggregated_skus:
                        global_aggregated_skus[sku_text] += sku_quantity
                    else:
                        global_aggregated_skus[sku_text] = sku_quantity

            final_skus_to_stamp_on_this_page = []
            for sku, total_qty in page_aggregated_skus.items():
                final_skus_to_stamp_on_this_page.append(f"{sku} (x{total_qty})")
            
            final_skus_to_stamp_on_this_page.sort()

            if final_skus_to_stamp_on_this_page:
                final_text_to_stamp = "\n".join(final_skus_to_stamp_on_this_page)

                max_line_width = 0
                num_lines = 0
                
                try:
                    lines = final_text_to_stamp.split('\n')
                    if lines:
                        max_line_width = max(fitz.get_text_length(line, fontname=font_name, fontsize=font_size) for line in lines)
                    num_lines = len(lines)
                except Exception as e:
                    print(f"Warning: Error calculating text dimensions: {e}. Using default size for background.")
                    max_line_width = 100
                    num_lines = 1

                padding_x = 10
                padding_y = 5

                background_width = max_line_width + (2 * padding_x)
                background_height = (num_lines * font_size * 1.4) + (2 * padding_y)

                rect_x0 = left_margin
                rect_x1 = rect_x0 + background_width

                rect_y1 = output_page.rect.height - bottom_margin
                rect_y0 = rect_y1 - background_height

                background_rect = fitz.Rect(rect_x0, rect_y0, rect_x1, rect_y1)

                output_page.draw_rect(background_rect, color=(0.8, 0.8, 0.8), fill=(0.8, 0.8, 0.8))

                text_insert_x = rect_x0 + padding_x
                text_insert_y = rect_y0 + padding_y + font_size

                output_page.insert_text(
                    fitz.Point(text_insert_x, text_insert_y),
                    final_text_to_stamp,
                    fontname=font_name,
                    fontsize=font_size,
                    color=(0, 0, 0),
                    set_simple=True
                )
        
        first_page_dims = doc.load_page(0).rect
        page_width = first_page_dims.width
        page_height = first_page_dims.height
        summary_padding_x = 10
        summary_padding_y = 10
        top_margin_summary = 20
        available_content_height_per_page = page_height - (2 * bottom_margin) - (2 * summary_padding_y)

        def add_new_summary_page_content(page_obj, lines_to_stamp, title="", dynamic_font_sizing_enabled=False, position_top=False):
            content_elements_info = []
            max_content_width_on_page = 0
            
            max_width_for_text_area = page_width - (2 * left_margin) - (2 * summary_padding_x)

            if title:
                title_font_size_actual = font_size
                title_text_width = fitz.get_text_length(title, fontname=font_name, fontsize=title_font_size_actual)
                while title_text_width > max_width_for_text_area and title_font_size_actual > MIN_FONT_SIZE:
                    title_font_size_actual -= 0.5
                    title_text_width = fitz.get_text_length(title, fontname=font_name, fontsize=title_font_size_actual)
                
                content_elements_info.append((title, title_font_size_actual, title_font_size_actual * 1.8))
                max_content_width_on_page = max(max_content_width_on_page, title_text_width)
            
            for line in lines_to_stamp:
                current_line_font_size = font_size
                
                # Check if line needs to be split due to width
                text_width = fitz.get_text_length(line, fontname=font_name, fontsize=current_line_font_size)
                
                # Add extra width for bullet points if this line has a bullet
                if line.startswith("● "):
                    bullet_space = 15  # Space for bullet circle (3 radius + 2 margin + 6 spacing)
                    text_width += bullet_space
                
                if text_width > max_width_for_text_area:
                    # Split long lines by breaking at " / " separators or spaces
                    if " / " in line:
                        # Split at SKU separators first
                        parts = line.split(" / ")
                        current_line_parts = []
                        
                        for part in parts:
                            test_line = " / ".join(current_line_parts + [part])
                            test_width = fitz.get_text_length(test_line, fontname=font_name, fontsize=current_line_font_size)
                            
                            if test_width <= max_width_for_text_area:
                                current_line_parts.append(part)
                            else:
                                # Add current accumulated parts as a line
                                if current_line_parts:
                                    accumulated_line = " / ".join(current_line_parts)
                                    accumulated_width = fitz.get_text_length(accumulated_line, fontname=font_name, fontsize=current_line_font_size)
                                    if line.startswith("● "):
                                        accumulated_width += 15  # Add bullet space
                                    content_elements_info.append((accumulated_line, current_line_font_size, current_line_font_size * 1.4))
                                    max_content_width_on_page = max(max_content_width_on_page, accumulated_width)
                                
                                # Start new line with current part
                                current_line_parts = [part]
                        
                        # Add remaining parts
                        if current_line_parts:
                            final_line = " / ".join(current_line_parts)
                            final_width = fitz.get_text_length(final_line, fontname=font_name, fontsize=current_line_font_size)
                            if line.startswith("● "):
                                final_width += 15  # Add bullet space
                            content_elements_info.append((final_line, current_line_font_size, current_line_font_size * 1.4))
                            max_content_width_on_page = max(max_content_width_on_page, final_width)
                    else:
                        # Split at spaces for non-pattern lines
                        words = line.split()
                        current_line_words = []
                        
                        for word in words:
                            test_line = " ".join(current_line_words + [word])
                            test_width = fitz.get_text_length(test_line, fontname=font_name, fontsize=current_line_font_size)
                            
                            if test_width <= max_width_for_text_area:
                                current_line_words.append(word)
                            else:
                                # Add current accumulated words as a line
                                if current_line_words:
                                    accumulated_line = " ".join(current_line_words)
                                    accumulated_width = fitz.get_text_length(accumulated_line, fontname=font_name, fontsize=current_line_font_size)
                                    if line.startswith("● "):
                                        accumulated_width += 15  # Add bullet space
                                    content_elements_info.append((accumulated_line, current_line_font_size, current_line_font_size * 1.4))
                                    max_content_width_on_page = max(max_content_width_on_page, accumulated_width)
                                
                                # Start new line with current word
                                current_line_words = [word]
                        
                        # Add remaining words
                        if current_line_words:
                            final_line = " ".join(current_line_words)
                            final_width = fitz.get_text_length(final_line, fontname=font_name, fontsize=current_line_font_size)
                            if line.startswith("● "):
                                final_width += 15  # Add bullet space
                            content_elements_info.append((final_line, current_line_font_size, current_line_font_size * 1.4))
                            max_content_width_on_page = max(max_content_width_on_page, final_width)
                else:
                    # Line fits, add as-is
                    final_text_width = text_width
                    if line.startswith("● "):
                        final_text_width += 15  # Add bullet space for display width calculation
                    content_elements_info.append((line, current_line_font_size, current_line_font_size * 1.4))
                    max_content_width_on_page = max(max_content_width_on_page, final_text_width)

            total_content_height_on_page = sum(info[2] for info in content_elements_info) + (2 * summary_padding_y)

            bg_rect_x0 = left_margin
            bg_rect_x1 = left_margin + max_content_width_on_page + (2 * summary_padding_x)

            if position_top:
                bg_rect_y0 = top_margin_summary
                bg_rect_y1 = top_margin_summary + total_content_height_on_page
            else:
                bg_rect_y1 = page_height - bottom_margin
                bg_rect_y0 = bg_rect_y1 - total_content_height_on_page

            background_rect = fitz.Rect(bg_rect_x0, bg_rect_y0, bg_rect_x1, bg_rect_y1)

            page_obj.draw_rect(background_rect, color=(0.9, 0.9, 0.9), fill=(0.9, 0.9, 0.9))

            if position_top:
                current_y_cursor = top_margin_summary + summary_padding_y
                if content_elements_info:
                    current_y_cursor += content_elements_info[0][1]
                
                for text_content, font_size_actual, element_height_taken in content_elements_info:
                    if text_content != title or not title:
                        # Check if this line should have a bullet (starts with "● ")
                        if text_content.startswith("● "):
                            # Draw a circle bullet
                            bullet_radius = 3
                            bullet_x = left_margin + summary_padding_x + bullet_radius + 2
                            bullet_y = current_y_cursor - (font_size_actual * 0.3)
                            bullet_center = fitz.Point(bullet_x, bullet_y)
                            page_obj.draw_circle(bullet_center, bullet_radius, color=(0, 0, 0), fill=(0, 0, 0))
                            
                            # Insert text without the bullet symbol, with proper spacing
                            text_without_bullet = text_content[2:]  # Remove "● "
                            text_x = bullet_x + bullet_radius + 6
                            page_obj.insert_text(
                                fitz.Point(text_x, current_y_cursor),
                                text_without_bullet,
                                fontname=font_name,
                                fontsize=font_size_actual,
                                color=(0, 0, 0),
                                set_simple=True
                            )
                        else:
                            page_obj.insert_text(
                                fitz.Point(left_margin + summary_padding_x, current_y_cursor),
                                text_content,
                                fontname=font_name,
                                fontsize=font_size_actual,
                                color=(0, 0, 0),
                                set_simple=True
                            )
                        current_y_cursor += element_height_taken
                    else:
                         page_obj.insert_text(
                            fitz.Point(left_margin + summary_padding_x, current_y_cursor),
                            text_content,
                            fontname=font_name,
                            fontsize=font_size_actual,
                            color=(0, 0, 0),
                            set_simple=True
                        )
                         current_y_cursor += element_height_taken
            else:
                current_y_cursor = bg_rect_y0 + summary_padding_y + (content_elements_info[0][1] if content_elements_info else 0)
                for text_content, font_size_actual, element_height_taken in content_elements_info:
                    # Check if this line should have a bullet (starts with "● ")
                    if text_content.startswith("● "):
                        # Draw a circle bullet
                        bullet_radius = 3
                        bullet_x = left_margin + summary_padding_x + bullet_radius + 2
                        bullet_y = current_y_cursor - (font_size_actual * 0.3)
                        bullet_center = fitz.Point(bullet_x, bullet_y)
                        page_obj.draw_circle(bullet_center, bullet_radius, color=(0, 0, 0), fill=(0, 0, 0))
                        
                        # Insert text without the bullet symbol, with proper spacing
                        text_without_bullet = text_content[2:]  # Remove "● "
                        text_x = bullet_x + bullet_radius + 6
                        page_obj.insert_text(
                            fitz.Point(text_x, current_y_cursor),
                            text_without_bullet,
                            fontname=font_name,
                            fontsize=font_size_actual,
                            color=(0, 0, 0),
                            set_simple=True
                        )
                    else:
                        page_obj.insert_text(
                            fitz.Point(left_margin + summary_padding_x, current_y_cursor),
                            text_content,
                            fontname=font_name,
                            fontsize=font_size_actual,
                            color=(0, 0, 0),
                            set_simple=True
                        )
                    current_y_cursor -= element_height_taken
        
        if global_aggregated_skus:
            summary_text_lines = []
            sorted_global_skus = sorted(global_aggregated_skus.items())
            for sku, total_qty in sorted_global_skus:
                summary_text_lines.append(f"● {sku} (x{total_qty})")
            
            # Create a special 2-column layout for All SKUs Summary page
            def add_two_column_all_skus_page(page_obj, lines_to_display, title=""):
                # Calculate column dimensions
                available_width = page_width - (2 * left_margin) - (2 * summary_padding_x)
                column_width = (available_width - 20) / 2  # 20 points spacing between columns
                
                # Split lines into two columns
                mid_point = len(lines_to_display) // 2
                if len(lines_to_display) % 2 != 0:
                    mid_point += 1  # Put extra item in first column
                
                left_column_lines = lines_to_display[:mid_point]
                right_column_lines = lines_to_display[mid_point:]
                
                # Calculate title dimensions
                title_height = 0
                if title:
                    title_font_size_actual = font_size
                    title_text_width = fitz.get_text_length(title, fontname=font_name, fontsize=title_font_size_actual)
                    while title_text_width > available_width and title_font_size_actual > MIN_FONT_SIZE:
                        title_font_size_actual -= 0.5
                        title_text_width = fitz.get_text_length(title, fontname=font_name, fontsize=title_font_size_actual)
                    title_height = title_font_size_actual * 1.8
                
                # Calculate content height for background
                max_column_height = max(len(left_column_lines), len(right_column_lines)) * (font_size * 1.4)
                total_content_height = title_height + max_column_height + (2 * summary_padding_y)
                
                # Draw background
                bg_rect_x0 = left_margin
                bg_rect_x1 = left_margin + available_width + (2 * summary_padding_x)
                bg_rect_y0 = top_margin_summary
                bg_rect_y1 = top_margin_summary + total_content_height
                
                background_rect = fitz.Rect(bg_rect_x0, bg_rect_y0, bg_rect_x1, bg_rect_y1)
                page_obj.draw_rect(background_rect, color=(0.9, 0.9, 0.9), fill=(0.9, 0.9, 0.9))
                
                # Draw title
                current_y = top_margin_summary + summary_padding_y
                if title:
                    current_y += title_font_size_actual
                    page_obj.insert_text(
                        fitz.Point(left_margin + summary_padding_x, current_y),
                        title,
                        fontname=font_name,
                        fontsize=title_font_size_actual,
                        color=(0, 0, 0),
                        set_simple=True
                    )
                    current_y += title_font_size_actual * 0.8  # Add some spacing after title
                
                # Draw left column
                left_column_x = left_margin + summary_padding_x
                current_left_y = current_y + font_size
                
                for line in left_column_lines:
                    if line.startswith("● "):
                        # Draw bullet
                        bullet_radius = 3
                        bullet_x = left_column_x + bullet_radius + 2
                        bullet_y = current_left_y - (font_size * 0.3)
                        bullet_center = fitz.Point(bullet_x, bullet_y)
                        page_obj.draw_circle(bullet_center, bullet_radius, color=(0, 0, 0), fill=(0, 0, 0))
                        
                        # Draw text
                        text_without_bullet = line[2:]  # Remove "● "
                        text_x = bullet_x + bullet_radius + 6
                        page_obj.insert_text(
                            fitz.Point(text_x, current_left_y),
                            text_without_bullet,
                            fontname=font_name,
                            fontsize=font_size,
                            color=(0, 0, 0),
                            set_simple=True
                        )
                    else:
                        page_obj.insert_text(
                            fitz.Point(left_column_x, current_left_y),
                            line,
                            fontname=font_name,
                            fontsize=font_size,
                            color=(0, 0, 0),
                            set_simple=True
                        )
                    current_left_y += font_size * 1.4
                
                # Draw right column
                right_column_x = left_column_x + column_width + 20  # 20 points spacing
                current_right_y = current_y + font_size
                
                for line in right_column_lines:
                    if line.startswith("● "):
                        # Draw bullet
                        bullet_radius = 3
                        bullet_x = right_column_x + bullet_radius + 2
                        bullet_y = current_right_y - (font_size * 0.3)
                        bullet_center = fitz.Point(bullet_x, bullet_y)
                        page_obj.draw_circle(bullet_center, bullet_radius, color=(0, 0, 0), fill=(0, 0, 0))
                        
                        # Draw text
                        text_without_bullet = line[2:]  # Remove "● "
                        text_x = bullet_x + bullet_radius + 6
                        page_obj.insert_text(
                            fitz.Point(text_x, current_right_y),
                            text_without_bullet,
                            fontname=font_name,
                            fontsize=font_size,
                            color=(0, 0, 0),
                            set_simple=True
                        )
                    else:
                        page_obj.insert_text(
                            fitz.Point(right_column_x, current_right_y),
                            line,
                            fontname=font_name,
                            fontsize=font_size,
                            color=(0, 0, 0),
                            set_simple=True
                        )
                    current_right_y += font_size * 1.4

            # Check if all lines fit in one page with 2-column layout
            max_lines_per_page = int(available_content_height_per_page / (font_size * 1.4))
            max_lines_two_columns = max_lines_per_page * 2  # Since we have 2 columns
            
            if len(summary_text_lines) <= max_lines_two_columns:
                # All lines fit in one page with 2 columns
                new_page = output_doc.new_page(width=page_width, height=page_height)
                add_two_column_all_skus_page(new_page, summary_text_lines, "--- All SKUs Summary ---")
            else:
                # Need multiple pages - use 2-column for first page, then regular layout for overflow
                current_summary_lines_buffer = []
                current_buffer_height = 0
                page_count = 0
                
                estimated_line_height_fixed = font_size * 1.4
                
                for line in summary_text_lines:
                    if current_buffer_height + estimated_line_height_fixed > available_content_height_per_page:
                        new_page = output_doc.new_page(width=page_width, height=page_height)
                        if page_count == 0:
                            # First page uses 2-column layout
                            add_two_column_all_skus_page(new_page, current_summary_lines_buffer, "--- All SKUs Summary ---")
                        else:
                            # Subsequent pages use regular layout
                            add_new_summary_page_content(new_page, current_summary_lines_buffer, "--- All SKUs Summary (continued) ---", position_top=True)
                        current_summary_lines_buffer = [line]
                        current_buffer_height = estimated_line_height_fixed
                        page_count += 1
                    else:
                        current_summary_lines_buffer.append(line)
                        current_buffer_height += estimated_line_height_fixed
                
                if current_summary_lines_buffer:
                    new_page = output_doc.new_page(width=page_width, height=page_height)
                    if page_count == 0:
                        # Only page uses 2-column layout
                        add_two_column_all_skus_page(new_page, current_summary_lines_buffer, "--- All SKUs Summary ---")
                    else:
                        # Final page uses regular layout
                        add_new_summary_page_content(new_page, current_summary_lines_buffer, "--- All SKUs Summary (continued) ---", position_top=True)

        # Multi-SKU Orders Pattern Summary
        multi_sku_pattern_counts = {}
        
        # Track which pages we've already processed to avoid double-counting two-page orders
        processed_pages = set()
        
        # Group SKUs by page and check for multi-SKU pages, handling two-page orders
        for page_num in range(doc.page_count):
            if page_num in processed_pages:
                continue
                
            if page_num in skus_by_page:
                # Start with SKUs from current page
                combined_sku_aggregated = {}
                for sku_info in skus_by_page[page_num]:
                    sku_text = sku_info['sku']
                    sku_quantity = sku_info['quantity']
                    if sku_text in combined_sku_aggregated:
                        combined_sku_aggregated[sku_text] += sku_quantity
                    else:
                        combined_sku_aggregated[sku_text] = sku_quantity
                
                # Check if this is a two-page order by looking at the next page
                is_two_page_order = False
                if page_num + 1 < doc.page_count:
                    current_page_text = doc.load_page(page_num).get_text()
                    next_page_text = doc.load_page(page_num + 1).get_text()
                    
                    # Check if current page has "Payment" and next page doesn't
                    if "Payment" in current_page_text and "Payment" not in next_page_text:
                        is_two_page_order = True
                        
                        # Add SKUs from the next page to the combined aggregation
                        if page_num + 1 in skus_by_page:
                            for sku_info in skus_by_page[page_num + 1]:
                                sku_text = sku_info['sku']
                                sku_quantity = sku_info['quantity']
                                if sku_text in combined_sku_aggregated:
                                    combined_sku_aggregated[sku_text] += sku_quantity
                                else:
                                    combined_sku_aggregated[sku_text] = sku_quantity
                        
                        # Mark next page as processed so we don't count it separately
                        processed_pages.add(page_num + 1)
                
                # Check if this order (single or two-page) has more than one unique SKU
                if len(combined_sku_aggregated) > 1:
                    # Create pattern string for this order
                    sorted_order_skus = sorted(combined_sku_aggregated.items())
                    pattern_parts = []
                    for sku, total_qty in sorted_order_skus:
                        pattern_parts.append(f"{sku} (x{total_qty})")
                    
                    pattern = " / ".join(pattern_parts)
                    
                    # Count this pattern
                    if pattern in multi_sku_pattern_counts:
                        multi_sku_pattern_counts[pattern] += 1
                    else:
                        multi_sku_pattern_counts[pattern] = 1
                
                # Mark current page as processed
                processed_pages.add(page_num)

        # Create Multi-SKU Orders summary page if there are any patterns
        if multi_sku_pattern_counts:
            multi_sku_summary_lines = []
            sorted_patterns = sorted(multi_sku_pattern_counts.items())
            for pattern, count in sorted_patterns:
                if count > 1:
                    multi_sku_summary_lines.append(f"● {pattern} - {count} orders")
                else:
                    multi_sku_summary_lines.append(f"● {pattern} - 1 order")

            # Process lines with proper page break handling for wrapped content
            current_multi_sku_lines_buffer = []
            current_buffer_height = 0
            
            # Define line height for calculations
            estimated_line_height_fixed = font_size * 1.4
            
            for line in multi_sku_summary_lines:
                # Calculate how many lines this entry will actually take after wrapping
                max_width_for_text_area = page_width - (2 * left_margin) - (2 * summary_padding_x)
                text_width = fitz.get_text_length(line, fontname=font_name, fontsize=font_size)
                
                # Estimate number of lines this entry will take
                estimated_lines_for_this_entry = 1
                if text_width > max_width_for_text_area:
                    if " / " in line:
                        # Count SKU parts to estimate wrapped lines
                        parts = line.split(" / ")
                        current_test_parts = []
                        line_count = 0
                        
                        for part in parts:
                            test_line = " / ".join(current_test_parts + [part])
                            test_width = fitz.get_text_length(test_line, fontname=font_name, fontsize=font_size)
                            
                            if test_width <= max_width_for_text_area:
                                current_test_parts.append(part)
                            else:
                                if current_test_parts:
                                    line_count += 1
                                current_test_parts = [part]
                        
                        if current_test_parts:
                            line_count += 1
                        
                        estimated_lines_for_this_entry = max(1, line_count)
                    else:
                        # Estimate based on character count for word wrapping
                        estimated_lines_for_this_entry = max(1, int(text_width / max_width_for_text_area) + 1)
                
                estimated_height_for_this_entry = estimated_lines_for_this_entry * estimated_line_height_fixed
                
                # Check if adding this entry would exceed page height
                if current_buffer_height + estimated_height_for_this_entry > available_content_height_per_page:
                    # Create page with current buffer
                    if current_multi_sku_lines_buffer:
                        new_page = output_doc.new_page(width=page_width, height=page_height)
                        add_new_summary_page_content(new_page, current_multi_sku_lines_buffer, "--- Mix Orders Patterns ---", position_top=True)
                    
                    # Start new page with current line
                    current_multi_sku_lines_buffer = [line]
                    current_buffer_height = estimated_height_for_this_entry
                else:
                    # Add to current buffer
                    current_multi_sku_lines_buffer.append(line)
                    current_buffer_height += estimated_height_for_this_entry
            
            # Create final page if there's remaining content
            if current_multi_sku_lines_buffer:
                new_page = output_doc.new_page(width=page_width, height=page_height)
                add_new_summary_page_content(new_page, current_multi_sku_lines_buffer, "--- Mix Orders Patterns ---", position_top=True)

        # Multi-SKU Orders SKU Count Summary
        if multi_sku_pattern_counts:
            # Aggregate SKU counts from all multi-SKU patterns
            multi_sku_count_aggregated = {}
            
            for pattern, occurrence_count in multi_sku_pattern_counts.items():
                # Parse the pattern to extract individual SKUs and their quantities
                # Pattern format: "BWL (x1) / BWM (x1) - 44 orders"
                # Remove the order count part first
                pattern_without_count = pattern.split(" - ")[0] if " - " in pattern else pattern
                
                # Split by " / " to get individual SKU parts
                sku_parts = pattern_without_count.split(" / ")
                
                for sku_part in sku_parts:
                    # Extract SKU name and quantity from format "BWL (x1)"
                    if " (x" in sku_part and sku_part.endswith(")"):
                        sku_name = sku_part.split(" (x")[0].strip()
                        quantity_str = sku_part.split(" (x")[1].rstrip(")")
                        try:
                            sku_quantity = int(quantity_str)
                            # Multiply by the number of times this pattern occurred
                            total_sku_quantity = sku_quantity * occurrence_count
                            
                            if sku_name in multi_sku_count_aggregated:
                                multi_sku_count_aggregated[sku_name] += total_sku_quantity
                            else:
                                multi_sku_count_aggregated[sku_name] = total_sku_quantity
                        except ValueError:
                            continue  # Skip if quantity parsing fails
            
            # Create Multi-SKU Orders SKU Count summary page if there are any counts
            if multi_sku_count_aggregated:
                multi_sku_count_lines = []
                sorted_multi_sku_counts = sorted(multi_sku_count_aggregated.items())
                for sku, total_qty in sorted_multi_sku_counts:
                    multi_sku_count_lines.append(f"● {sku} (x{total_qty})")

                # Create a special 2-column layout for SKU count page
                def add_two_column_summary_page(page_obj, lines_to_display, title=""):
                    # Calculate column dimensions
                    available_width = page_width - (2 * left_margin) - (2 * summary_padding_x)
                    column_width = (available_width - 20) / 2  # 20 points spacing between columns
                    
                    # Split lines into two columns
                    mid_point = len(lines_to_display) // 2
                    if len(lines_to_display) % 2 != 0:
                        mid_point += 1  # Put extra item in first column
                    
                    left_column_lines = lines_to_display[:mid_point]
                    right_column_lines = lines_to_display[mid_point:]
                    
                    # Calculate title dimensions
                    title_height = 0
                    if title:
                        title_font_size_actual = font_size
                        title_text_width = fitz.get_text_length(title, fontname=font_name, fontsize=title_font_size_actual)
                        while title_text_width > available_width and title_font_size_actual > MIN_FONT_SIZE:
                            title_font_size_actual -= 0.5
                            title_text_width = fitz.get_text_length(title, fontname=font_name, fontsize=title_font_size_actual)
                        title_height = title_font_size_actual * 1.8
                    
                    # Calculate content height for background
                    max_column_height = max(len(left_column_lines), len(right_column_lines)) * (font_size * 1.4)
                    total_content_height = title_height + max_column_height + (2 * summary_padding_y)
                    
                    # Draw background
                    bg_rect_x0 = left_margin
                    bg_rect_x1 = left_margin + available_width + (2 * summary_padding_x)
                    bg_rect_y0 = top_margin_summary
                    bg_rect_y1 = top_margin_summary + total_content_height
                    
                    background_rect = fitz.Rect(bg_rect_x0, bg_rect_y0, bg_rect_x1, bg_rect_y1)
                    page_obj.draw_rect(background_rect, color=(0.9, 0.9, 0.9), fill=(0.9, 0.9, 0.9))
                    
                    # Draw title
                    current_y = top_margin_summary + summary_padding_y
                    if title:
                        current_y += title_font_size_actual
                        page_obj.insert_text(
                            fitz.Point(left_margin + summary_padding_x, current_y),
                            title,
                            fontname=font_name,
                            fontsize=title_font_size_actual,
                            color=(0, 0, 0),
                            set_simple=True
                        )
                        current_y += title_font_size_actual * 0.8  # Add some spacing after title
                    
                    # Draw left column
                    left_column_x = left_margin + summary_padding_x
                    current_left_y = current_y + font_size
                    
                    for line in left_column_lines:
                        if line.startswith("● "):
                            # Draw bullet
                            bullet_radius = 3
                            bullet_x = left_column_x + bullet_radius + 2
                            bullet_y = current_left_y - (font_size * 0.3)
                            bullet_center = fitz.Point(bullet_x, bullet_y)
                            page_obj.draw_circle(bullet_center, bullet_radius, color=(0, 0, 0), fill=(0, 0, 0))
                            
                            # Draw text
                            text_without_bullet = line[2:]  # Remove "● "
                            text_x = bullet_x + bullet_radius + 6
                            page_obj.insert_text(
                                fitz.Point(text_x, current_left_y),
                                text_without_bullet,
                                fontname=font_name,
                                fontsize=font_size,
                                color=(0, 0, 0),
                                set_simple=True
                            )
                        else:
                            page_obj.insert_text(
                                fitz.Point(left_column_x, current_left_y),
                                line,
                                fontname=font_name,
                                fontsize=font_size,
                                color=(0, 0, 0),
                                set_simple=True
                            )
                        current_left_y += font_size * 1.4
                    
                    # Draw right column
                    right_column_x = left_column_x + column_width + 20  # 20 points spacing
                    current_right_y = current_y + font_size
                    
                    for line in right_column_lines:
                        if line.startswith("● "):
                            # Draw bullet
                            bullet_radius = 3
                            bullet_x = right_column_x + bullet_radius + 2
                            bullet_y = current_right_y - (font_size * 0.3)
                            bullet_center = fitz.Point(bullet_x, bullet_y)
                            page_obj.draw_circle(bullet_center, bullet_radius, color=(0, 0, 0), fill=(0, 0, 0))
                            
                            # Draw text
                            text_without_bullet = line[2:]  # Remove "● "
                            text_x = bullet_x + bullet_radius + 6
                            page_obj.insert_text(
                                fitz.Point(text_x, current_right_y),
                                text_without_bullet,
                                fontname=font_name,
                                fontsize=font_size,
                                color=(0, 0, 0),
                                set_simple=True
                            )
                        else:
                            page_obj.insert_text(
                                fitz.Point(right_column_x, current_right_y),
                                line,
                                fontname=font_name,
                                fontsize=font_size,
                                color=(0, 0, 0),
                                set_simple=True
                            )
                        current_right_y += font_size * 1.4

                # Check if all lines fit in one page with 2-column layout
                max_lines_per_page = int(available_content_height_per_page / (font_size * 1.4))
                max_lines_two_columns = max_lines_per_page * 2  # Since we have 2 columns
                
                # Define line height for calculations
                estimated_line_height_fixed = font_size * 1.4
                
                if len(multi_sku_count_lines) <= max_lines_two_columns:
                    # All lines fit in one page with 2 columns
                    new_page = output_doc.new_page(width=page_width, height=page_height)
                    add_two_column_summary_page(new_page, multi_sku_count_lines, "--- Mix Orders SKU Count ---")
                else:
                    # Need multiple pages - use regular single column layout for overflow
                    current_multi_sku_count_buffer = []
                    current_buffer_height = 0
                    page_count = 0
                    
                    for line in multi_sku_count_lines:
                        if current_buffer_height + estimated_line_height_fixed > available_content_height_per_page:
                            new_page = output_doc.new_page(width=page_width, height=page_height)
                            if page_count == 0:
                                # First page uses 2-column layout
                                add_two_column_summary_page(new_page, current_multi_sku_count_buffer, "--- Mix Orders SKU Count ---")
                            else:
                                # Subsequent pages use regular layout
                                add_new_summary_page_content(new_page, current_multi_sku_count_buffer, "--- Mix Orders SKU Count (continued) ---", position_top=True)
                            current_multi_sku_count_buffer = [line]
                            current_buffer_height = estimated_line_height_fixed
                            page_count += 1
                        else:
                            current_multi_sku_count_buffer.append(line)
                            current_buffer_height += estimated_line_height_fixed
                    
                    if current_multi_sku_count_buffer:
                        new_page = output_doc.new_page(width=page_width, height=page_height)
                        if page_count == 0:
                            # Only page uses 2-column layout
                            add_two_column_summary_page(new_page, current_multi_sku_count_buffer, "--- Mix Orders SKU Count ---")
                        else:
                            # Final page uses regular layout
                            add_new_summary_page_content(new_page, current_multi_sku_count_buffer, "--- Mix Orders SKU Count (continued) ---", position_top=True)

                
        output_doc.save(output_pdf_path)
        output_doc.close()
        doc.close()
        return True
    except Exception as e:
        print(f"An error occurred during PDF stamping: {e}")
        return False

def main(file_name=None):
    """
    Main function to run the SKU extraction and stamping process.
    """
    print("--- Waybill SKU Stamping Tool with Quantity (End of Page Stamp) ---")
    print("This script will will read a PDF waybill, identify SKU codes and quantities,")
    print("and create a new PDF with the SKUs (and quantities) stamped (black text on light gray background).")
    print("\nNote: The script will now scan the entire page for SKUs, without restricting to the last 10%.")
    print("      SKUs starting with 'C_' or 'C ' will have the prefix removed when stamped.")
    print("      If an SKU contains 'B1T1', it will be removed from the SKU text and its quantity will be doubled.")
    print("      If an SKU contains a '/', it will be split into multiple SKUs during extraction, each stamped with the calculated quantity.")
    print("      If an SKU ends with a number (e.g., 'SKU-ABC-3'), that number will be multiplied by the quantity,")
    print("      and the number will be removed from the SKU text (universal application).")
    print("      If an 'xN' string (e.g., 'x2', 'X5') is found *within or beside* an SKU, that 'N' will be used as an additional multiplier for the quantity.")
    print("      Any leading or trailing dashes or underscores will be removed from the SKU text after number removal.")
    print("      Quantity will now ONLY be searched to the right of the SKU, on the same line or slightly below (vertical range increased to 40 points).")
    print("      All identified SKUs for a page will be stamped together at the page's bottom-left.")
    print("      Orders spanning two pages (current page has 'Payment', next page does not) will have SKUs from the first page moved to the second page for stamping.")
    print("      Quantities for identical SKUs on the same page will now be summed and displayed as a single entry.")
    print("      A new summary page will be added at the end of the PDF, listing all unique SKUs and their total quantities across the entire file.")
    print("      SKU aliases 'WASH-L' will be treated as 'BWL' and 'WASH-M' as 'BWM' before stamping and aggregation.")
    print("      You can adjust 'bottom_margin' and 'left_margin' in the 'stamp_skus_on_pdf' function")
    print("      for trial and error to fine-tune the stamp position.")
    print("      Also, ensure you have 'PyMuPDF' installed (`pip install PyMuPDF`).")
    print("      The multi-SKU summary will now correctly consolidate identical multi-SKU order patterns and add a count.")

    pdf_file_path = None

    if len(sys.argv) > 1:
            file_name = sys.argv[1]
            pdf_file_path = file_name.strip()
    else:
        pdf_file_path = input("\nEnter the full path to your waybill PDF file: ").strip()

    if not os.path.exists(pdf_file_path):
        print(f"Error: The specified file does not exist at '{pdf_file_path}'. Please check the path and try again.")
        return

    base_name = os.path.splitext(os.path.basename(pdf_file_path))[0]
    output_pdf_path = f"{base_name}_SKUs_Qty_EndPage.pdf"
    print(f"Output PDF will be saved as: {output_pdf_path}")

    sku_locations = extract_sku_locations_from_pdf(pdf_file_path)

    if sku_locations is None:
        print("Failed to extract SKU locations from the PDF. Exiting.")
        return

    if not sku_locations:
        print("No SKUs were identified in the PDF using the current patterns.")
        return

    print(f"\nIdentified {len(sku_locations)} potential SKUs.")
    print("--- Extracted SKUs per Page (before stamping) ---")
    for sku_info in sku_locations:
        print(f"  Page {sku_info['page_num'] + 1}: SKU='{sku_info['sku']}', Quantity={sku_info['quantity']}, Order ID='{sku_info['order_id']}'")
    print("--------------------------------------------------")

    multi_sku_orders = {}
    for sku_info in sku_locations:
        order_id = sku_info.get('order_id', 'UNKNOWN_ORDER')
        if order_id not in multi_sku_orders:
            multi_sku_orders[order_id] = []
        multi_sku_orders[order_id].append(sku_info)

    filtered_multi_sku_orders = {}
    for order_id, skus_list in multi_sku_orders.items():
        unique_skus_in_order = set(sku_info['sku'] for sku_info in skus_list)
        if len(unique_skus_in_order) > 1:
            filtered_multi_sku_orders[order_id] = skus_list
    
    print(f"\nStamping them onto a new PDF...")

    if stamp_skus_on_pdf(pdf_file_path, sku_locations, output_pdf_path, filtered_multi_sku_orders):
        print(f"\nSuccessfully created '{output_pdf_path}' with SKUs and quantities.")
    else:
        print("\nFailed to create the output PDF.")

    print("\n--- End of SKU Stamping Process ---")

if __name__ == "__main__":
    if len(sys.argv) > 1:
            file_name = sys.argv[1]
            main(file_name)
    else:
        main()

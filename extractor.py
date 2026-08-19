import fitz  # PyMuPDF
import re

def extract_roll_numbers_from_pdf(pdf_path: str, regex_pattern: str = None) -> list[str]:
    """
    Extracts roll numbers from a PDF file.
    If regex_pattern is provided and is not 'auto', uses it.
    If regex_pattern is None, empty, or 'auto', auto-detects the roll number pattern.
    """
    try:
        doc = fitz.open(pdf_path)
    except Exception as e:
        print(f"Error opening PDF: {e}")
        return []

    # If a specific custom regex pattern is provided, use the old behavior
    if regex_pattern and regex_pattern.strip() and regex_pattern.strip() != "auto":
        roll_numbers = set()
        try:
            pattern = re.compile(regex_pattern)
            for page_num in range(len(doc)):
                page = doc.load_page(page_num)
                text = page.get_text()
                matches = pattern.findall(text)
                roll_numbers.update(matches)
        except Exception as e:
            print(f"Error using custom pattern: {e}")
        finally:
            doc.close()
        return list(roll_numbers)

    # --- AUTO-DETECTION MODE ---
    # We want to find the most likely roll number tokens.
    # We define a candidate token by splitting on whitespace and cleaning outer punctuation.
    
    # Track which pages each token appears on.
    # token -> set of page numbers
    token_pages = {}
    # Count of tokens grouped by length: length -> set of unique tokens
    length_unique_tokens = {l: set() for l in range(3, 21)}

    total_pages = len(doc)

    for page_num in range(total_pages):
        try:
            page = doc.load_page(page_num)
            text = page.get_text()
            # Find all potential tokens by splitting on whitespace
            tokens = text.split()
            for token in tokens:
                # Clean up outer punctuation
                token_clean = token.strip(".,:;()[]{}*\"'#$/\\-_ ")
                if not token_clean:
                    continue
                # Must contain at least one digit
                if not any(c.isdigit() for c in token_clean):
                    continue
                length = len(token_clean)
                if 3 <= length <= 20:
                    if token_clean not in token_pages:
                        token_pages[token_clean] = set()
                    token_pages[token_clean].add(page_num)
                    length_unique_tokens[length].add(token_clean)
        except Exception as e:
            print(f"Error reading page {page_num}: {e}")

    doc.close()

    # Determine the dominant length
    # We only consider lengths that have at least 3 unique tokens
    valid_lengths = []
    for length, unique_set in length_unique_tokens.items():
        if len(unique_set) >= 3:
            # Calculate average digit ratio to prioritize numeric roll numbers over ranks/codes
            total_digits = sum(sum(c.isdigit() for c in t) for t in unique_set)
            digit_ratio = total_digits / (len(unique_set) * length)
            valid_lengths.append((length, len(unique_set), digit_ratio))

    if not valid_lengths:
        # Fallback if no clear pattern detected: try 10 digit numbers
        fallback_len = 10
        if fallback_len in length_unique_tokens and length_unique_tokens[fallback_len]:
            detected_length = fallback_len
        else:
            return []
    else:
        # Pick the length with the maximum number of unique tokens, tie-breaking by digit ratio
        valid_lengths.sort(key=lambda x: (x[1], x[2]), reverse=True)
        detected_length = valid_lengths[0][0]

    # Filter candidates of the detected length:
    # Exclude tokens that appear on too many pages (e.g. headers/footers)
    # If the document has many pages, we exclude tokens appearing on > 15% of pages.
    # If total_pages is small (e.g. 1 or 2), we don't filter.
    final_roll_numbers = []
    max_allowed_pages = max(2, int(total_pages * 0.15))
    
    for token in length_unique_tokens[detected_length]:
        pages_present = len(token_pages[token])
        if total_pages <= 2 or pages_present <= max_allowed_pages:
            final_roll_numbers.append(token)

    return final_roll_numbers


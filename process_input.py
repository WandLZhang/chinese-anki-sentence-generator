def process_file(filename):
    # Read all lines from the file
    with open(filename, 'r', encoding='utf-8') as file:
        lines = file.readlines()
    
    # Extract words before second tab, keeping the first tab
    processed_lines = []
    for line in lines:
        if line.strip():  # Skip empty lines
            parts = line.split('\t', 1)  # Split on first tab only
            if parts:
                processed_lines.append(parts[0] + '\t\n')
    
    # Write back to the same file
    with open(filename, 'w', encoding='utf-8') as file:
        file.writelines(processed_lines)

# Process the file
process_file('input.txt')
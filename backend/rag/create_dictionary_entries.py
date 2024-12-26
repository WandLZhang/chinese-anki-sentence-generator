import os
from tqdm import tqdm

def create_dictionary_entries(input_file, output_dir):
    """
    Splits a dictionary file into individual text files for each entry.
    
    Args:
        input_file (str): Path to the input dictionary file
        output_dir (str): Directory to save individual entry files
    """
    # Create output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)
    
    # First, count total number of entries for progress bar
    total_entries = sum(1 for line in open(input_file, 'r', encoding='utf-8') 
                       if line.strip() and line[0].isdigit() and ',' in line)
    
    # Initialize variables
    current_entry = []
    
    # Create progress bar
    with tqdm(total=total_entries, desc="Creating dictionary entries") as pbar:
        with open(input_file, 'r', encoding='utf-8') as f:
            for line in f:
                # Strip whitespace
                line = line.strip()
                
                # Skip empty lines
                if not line:
                    continue
                    
                # Check if this line starts with a number (new entry)
                if line[0].isdigit() and ',' in line:
                    # If we have a previous entry, save it
                    if current_entry:
                        save_entry(current_entry, output_dir)
                        pbar.update(1)
                    
                    # Start new entry
                    current_entry = [line]
                else:
                    # Add line to current entry
                    current_entry.append(line)
            
            # Save the last entry
            if current_entry:
                save_entry(current_entry, output_dir)
                pbar.update(1)

def save_entry(entry_lines, output_dir):
    """
    Saves a single dictionary entry to a text file.
    
    Args:
        entry_lines (list): Lines of the dictionary entry
        output_dir (str): Directory to save the file
    """
    # Get the entry ID from the first line
    first_line = entry_lines[0]
    entry_id = first_line.split(',')[0]
    
    # Create filename
    filename = f"entry_{entry_id}.txt"
    filepath = os.path.join(output_dir, filename)
    
    # Write entry to file
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write('\n'.join(entry_lines))

def main():
    # Define paths relative to script location
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_dir = os.path.dirname(script_dir)
    
    input_file = os.path.join(project_dir, 'dictionaries', 'wordshk-dictionary.txt')
    output_dir = os.path.join(project_dir, 'dictionary_entries')
    
    # Process dictionary entries
    create_dictionary_entries(input_file, output_dir)
    print(f"\nFinished creating dictionary entries in {output_dir}")

if __name__ == "__main__":
    main()
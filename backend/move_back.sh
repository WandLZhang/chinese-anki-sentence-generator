#!/bin/bash

# Change to the dictionary_entries directory
cd dictionary_entries || exit 1

# Check if done directory exists
if [ ! -d "done" ]; then
    echo "No 'done' directory found in dictionary_entries"
    exit 1
fi

# Count files before moving
file_count=$(ls done/entry_*.txt 2>/dev/null | wc -l)
echo "Found $file_count files to move"

# Move files using a loop with progress indicator
echo "Moving files..."
count=0
total=$(find done -maxdepth 1 -name "entry_*.txt" | wc -l)

for file in done/entry_*.txt; do
    mv "$file" .
    count=$((count + 1))
    
    # Show progress every 1000 files
    if [ $((count % 1000)) -eq 0 ]; then
        echo "Moved $count of $total files..."
    fi
done

# Check if any files remain
remaining_files=$(find done -maxdepth 1 -name "entry_*.txt" | wc -l)

if [ $remaining_files -eq 0 ]; then
    echo "Successfully moved $count files back to dictionary_entries"
else
    echo "Error: $remaining_files files were not moved"
    exit 1
fi
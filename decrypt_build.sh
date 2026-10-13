# /bin/bash
# decrypt all elements in ./dockervolume/*.age using age
# expects an age identity file at ./keys.txt

# check if the identity file exists
# if not, error
if [ ! -f "./keys.txt" ]; then
    echo "Identity file not found"
    exit 1
fi

shopt -s nullglob

found=false
for file in ./dockervolume/*.age; do
    found=true
    if age -d -i "./keys.txt" -o "${file%.age}" "$file"; then
        rm -- "$file"
        echo "Decrypted $file"
    else
        echo "Failed to decrypt $file" >&2
        exit 1
    fi
done

if [ "$found" = false ]; then
    echo "No .age files found in ./dockervolume"
fi

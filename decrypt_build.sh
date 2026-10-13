# /bin/bash
# decrypt all elements in ./dockervolume/*.age using age
# expects an age identity file at ./keys.txt

# check if the identity file exists
# if not, error
if [ ! -f "./keys.txt" ]; then
    echo "Identity file not found"
    exit 1
fi

# loop over all age files in ./Build
for file in ./dockervolume/*.age; do
    # decrypt the file using age
    age -d -i "./keys.txt" -o "${file%.age}" "$file"
    # remove the original file
    rm "$file"
    echo "Decrypted $file"
done

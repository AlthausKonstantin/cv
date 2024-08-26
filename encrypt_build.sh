# /bin/bash
# encrypt all elements in ./Build/*.pdf using age
# if the env var AGE_RECIPIENT exists use its content as a recipient
# else error 

# check if the env var AGE_RECIPIENT exists
if [ -z "$AGE_RECIPIENT" ]; then
    echo "AGE_RECIPIENT is not set"
    exit 1
fi

# loop over all pdfs in ./Build
for file in ./Build/*.pdf; do
    # encrypt the file using age
    age -r $AGE_RECIPIENT -o "$file.age"  "$file"
    # remove the original file
    rm "$file"
    echo "Encrypted $file"
done

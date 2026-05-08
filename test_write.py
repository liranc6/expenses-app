import os
print("Testing write to file system")
with open("test_file.txt", "w") as f:
    f.write("Hello World")
print("Success" if os.path.exists("test_file.txt") else "Failed")

file = "backup/xbl_sc_logs.img"

def to_ascii(file):
    with open(file, "rb") as f:
        data = f.read()
        print(data)
    with open("out.txt", "w") as f:
        f.write(data.decode("ascii"))

if __name__ == "__main__":
    to_ascii(file)
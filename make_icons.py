from PIL import Image, ImageDraw

def make(size, path):
    img = Image.new("RGBA", (size, size), (11, 19, 32, 255))
    d = ImageDraw.Draw(img)
    d.rounded_rectangle((size*0.08, size*0.08, size*0.92, size*0.92), radius=int(size*0.22), fill=(18, 34, 46, 255))
    d.ellipse((size*0.18, size*0.18, size*0.82, size*0.82), fill=(0, 255, 136, 255))
    d.polygon([(size*0.50, size*0.28), (size*0.68, size*0.74), (size*0.60, size*0.74),
               (size*0.56, size*0.62), (size*0.44, size*0.62), (size*0.40, size*0.74),
               (size*0.32, size*0.74)], fill=(0,0,0,255))
    img.save(path)

if __name__ == "__main__":
    make(192, r"static\icon-192.png")
    make(512, r"static\icon-512.png")
    print("icons ok")

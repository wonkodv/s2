import pathlib
import requests


p = pathlib.Path(".")
s = []
for y in range(32):
    for x in range(32):
        i = p/f"{x:02d}x{y:02d}.jpg"
        if not i.exists():
            print(f"Download {i}")
            i.write_bytes(requests.get("https://media.gtanet.com/gta4/images/map/tiles/5_{:02d}.jpg".format(32*y+x+1)).content)
        s.append(f"<img src='{i}'>")
    s.append("<br>")

s="".join(s)

(p/"index.html").write_text("""
<!DOCTYPE html>
<html>
<head>
<style>
img {
padding:0;
margin:0;
}
body {
overflow:scroll;
line-height:0;
}

</style>
</head>
<body>
<pre>
"""+s+"""
</pre>
</body>
</html>
""")

import os
import aiohttp
import asyncio
import uvicorn
from uvicorn.loops.uvloop import uvloop_setup
# from fastai import *
# from fastai.vision import *
from deoldify.visualize import *
from io import BytesIO
from starlette.applications import Starlette
from starlette.middleware.cors import CORSMiddleware
from starlette.responses import HTMLResponse, JSONResponse
from starlette.staticfiles import StaticFiles
import PIL
import functools

export_file_url = 'https://www.googleapis.com/drive/v3/files/1HZlBbrDA7YWMutTxOX4KYIH59Ew-UnRg?alt=media&key=AIzaSyBf68scFs7oC5OUfPt2H1e70mLOdamfIus'
export_file_name = 'ColorizeArtistic_gen.pth'

path = Path(__file__).parent

app = Starlette()
app.add_middleware(CORSMiddleware, allow_origins=['*'], allow_headers=['X-Requested-With', 'Content-Type'])
app.mount('/static', StaticFiles(directory='static'))


async def image_transpose_exif(im):
    """
        Apply Image.transpose to ensure 0th row of pixels is at the visual
        top of the image, and 0th column is the visual left-hand side.
        Return the original image if unable to determine the orientation.

        As per CIPA DC-008-2012, the orientation field contains an integer,
        1 through 8. Other values are reserved.
    """

    exif_orientation_tag = 0x0112
    exif_transpose_sequences = [  # Val  0th row  0th col
        [],  # 0    (reserved)
        [],  # 1   top      left
        [PIL.Image.FLIP_LEFT_RIGHT],  # 2   top      right
        [PIL.Image.ROTATE_180],  # 3   bottom   right
        [PIL.Image.FLIP_TOP_BOTTOM],  # 4   bottom   left
        [PIL.Image.FLIP_LEFT_RIGHT, Image.ROTATE_90],  # 5   left     top
        [PIL.Image.ROTATE_270],  # 6   right    top
        [PIL.Image.FLIP_TOP_BOTTOM, Image.ROTATE_90],  # 7   right    bottom
        [PIL.Image.ROTATE_90],  # 8   left     bottom
    ]

    try:
        seq = exif_transpose_sequences[im._getexif()[exif_orientation_tag]]
    except Exception:
        return im
    else:
        return functools.reduce(type(im).transpose, seq, im)

async def download_file(url, dest):
    if dest.exists(): return
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            data = await response.read()
            with open(dest, 'wb') as f:
                f.write(data)


async def setup_learner():
    await download_file(export_file_url, path / 'models' / export_file_name)
    try:
        print('Load colorizer')
        colorizer = get_artistic_image_colorizer(root_folder=path, weights_name='ColorizeArtistic_gen')
        return colorizer
    except RuntimeError as e:
        if len(e.args) > 0 and 'CPU-only machine' in e.args[0]:
            print(e)
            message = "\n\nThis model was trained with an old version of fastai and will not work in a CPU environment.\n\nPlease update the fastai library in your training environment and export your model again.\n\nSee instructions for 'Returning to work' at https://course.fast.ai."
            raise RuntimeError(message)
        else:
            raise

loop = asyncio.get_event_loop()
tasks = [asyncio.ensure_future(setup_learner())]
colorizer = loop.run_until_complete(asyncio.gather(*tasks))[0]
loop.close()

# colorizer = None

@app.route('/')
async def homepage(request):
    html_file = path / 'view' / 'index.html'
    return HTMLResponse(html_file.open().read())


@app.route('/analyze', methods=['POST'])
async def analyze(request):
    # global colorizer
    # if not colorizer:
    #     colorizer = await setup_learner()
    buf = io.BytesIO()
    img_data = await request.form()
    img_bytes = await (img_data['file'].read())
    img = PIL.Image.open(BytesIO(img_bytes))
    img = await image_transpose_exif(img)
    img.thumbnail((1024, 1024))
    img = PIL.ImageOps.grayscale(img)
    img.save(buf, format="JPEG", optimize=True)
    buf.seek(0)
    prediction = colorizer.get_transformed_image(buf, render_factor=15)
    buf.seek(0)
    prediction.save(buf, format="JPEG", optimize=True)
    buf.seek(0)
    to_send = (b"data:image/jpeg;base64, " + base64.b64encode(buf.read())).decode("utf-8")
    return JSONResponse({'result': to_send})


if __name__ == '__main__':
    if 'serve' in sys.argv:
        port = int(os.environ.get('PORT', 5000))
        uvicorn.run(app=app, host='0.0.0.0', port=port, log_level="info")



"""
TODO:
- Long description text
"""
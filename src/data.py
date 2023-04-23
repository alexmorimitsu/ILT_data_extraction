import os
import pandas as pd
import numpy as np
import cv2
import tqdm
import PIL
import matplotlib.pyplot as plt
from matplotlib.offsetbox import OffsetImage, AnnotationBbox
from aux import defaults

# generate dataframe
def create_csv(df, csv_path):
    df = df.rename(columns={'klass': 'correct_label'})
    labels = df['correct_label'].tolist()
    df['correct_label'] = ['_' + str(l) for l in labels]

    classes = df['correct_label'].unique()
    classes.sort()
    map_color = {}
    for i in range(len(classes)):
        map_color[classes[i]] = i + 1

    df['manual_label'] = df['correct_label']
    list_colors = [map_color[c] for c in df['manual_label'].tolist()]
    df['colors'] = list_colors
    df['custom_data'] = [i for i in range(df.shape[0])]
    df['x2'] = [0] * df.shape[0]
    df['y2'] = [0] * df.shape[0]
    df['x3'] = [0] * df.shape[0]
    df['y3'] = [0] * df.shape[0]
    df['D1'] = [0] * df.shape[0]
    df['D4'] = [0] * df.shape[0]
    df['D7'] = [0] * df.shape[0]
    df['thumbnails'] = df['names'].copy()

    df.to_csv(csv_path, index=False)


# generate backgrounds
def get_image(path, paint=False, color=(1, 1, 1), zoom=0.2, dim=255):
    img = PIL.Image.open(path).convert('RGBA')
    img = np.array(img)
    if paint:
        img[:,:,0] = np.uint8(img[:,:,0] * color[0])
        img[:,:,1] = np.uint8(img[:,:,1] * color[1])
        img[:,:,2] = np.uint8(img[:,:,2] * color[2])
        img[:,:,3] = dim
    img = PIL.Image.fromarray(img)

    return OffsetImage(img, zoom=zoom)


def map_of_images(df, xrange, yrange, images_folder, output_path, zoom, fig_size=40):
    df_x = pd.to_numeric(df['x'])
    df_y = pd.to_numeric(df['y'])

    df_filtered = df[(df_x >= xrange[0]) & (df_x <= xrange[1]) & (df_y >= yrange[0]) & (df_y <= yrange[1])]

    x = df_filtered['x']
    y = df_filtered['y']
    names = df_filtered['names']

    f = plt.figure(figsize=(fig_size, fig_size), frameon=False)
    ax = plt.Axes(f, [0., 0., 1., 1.])
    ax.axis('off')
    f.add_axes(ax)
    ax.scatter(x, y, s=0)

    for xs, ys, name in zip(x, y, names):
        path = os.path.join(images_folder, name)
        ab = AnnotationBbox(get_image(path, zoom=zoom), (xs, ys), frameon=False, box_alignment=(0, 1))
        ax.add_artist(ab)

    ax.set_xlim(xrange)
    ax.set_ylim(yrange)
    f.savefig(output_path, bbox_inches='tight', pad_inches=0, dpi=100)

    plt.close(f)
    image = PIL.Image.open(output_path)

    return image


def add_scale(input_path, img_name):
    with tqdm.trange(len(listdir(input_path)), ascii=True) as pbar:
        for img_name in listdir(input_path):
            img = cv2.imread(os.path.join(input_path, img_name))
            img_out = np.zeros([img.shape[0] + 30, img.shape[1] + 20, 3])
            img_out = 255-img_out

            img_out[10:img.shape[0]+10,10:img.shape[1]+10] = img
            units = defaults['pixel_size'] * img.shape[1] * defaults['ruler_ratio']
            units = int(round(units/100))

            font = cv2.FONT_HERSHEY_SIMPLEX
            size = 100*units
            if size > 900:
                size = 1000
            ruler_size = int(round(size/defaults['pixel_size']))

            img_out = PIL.Image.fromarray(np.uint8(img_out)).convert('RGB')
            draw = PIL.ImageDraw.Draw(img_out)

            if size < 1000:
                text = str(size) + ' µm'
            else:
                text = str(int(size/1000)) + ' mm'
            draw.text((12, img.shape[0] + 12), text,(0, 0, 0))

            shape = [(10, img.shape[0] + 25), (ruler_size + 10, img.shape[0] + 25)]
            draw.line(shape, fill = 'black', width = 1)

            shape = [(10, img.shape[0] + 23), (10, img.shape[0] + 27)]
            draw.line(shape, fill = 'black', width = 1)

            shape = [(ruler_size + 10, img.shape[0] + 23), (ruler_size + 10, img.shape[0] + 27)]
            draw.line(shape, fill = 'black', width = 1)

            img_out.save(os.path.join(input_path, img_name))
            pbar.update(1)


# rescale image for thumbnails
def generate_thumbnails(input_path, thumbnails_folder, batch_id, max_size):
    if not os.path.isdir(thumbnails_folder):
        os.mkdir(thumbnails_folder, mode=0o755)

    thumbnails_path = os.path.join(thumbnails_folder, batch_id)
    if not os.path.isdir(thumbnails_path):
        os.mkdir(thumbnails_path, mode=0o755)

    inner_path = os.path.join(thumbnails_path, defaults['inner_folder'])
    if not os.path.isdir(inner_path):
        os.mkdir(inner_path, mode=0o755)

    for img_name in os.listdir(input_path):
        img = cv2.imread(os.path.join(input_path, img_name))
        if img.shape[0] > max_size:
            scale = img.shape[0] / max_size
            dims = (int(img.shape[1] / scale), int(img.shape[0] / scale))
            img = cv2.resize(img, dims, interpolation=cv2.INTER_AREA)

        output_name = os.path.join(inner_path, img_name)
        cv2.imwrite(output_name, img)


def generate_bkg(df_folder, images_folder, output_path, project_name, batch_id, range=100):
    df = pd.read_csv(os.path.join(df_folder, batch_id + '_' + project_name + '.csv'), index_col=None)

    backgrounds_folder = os.path.join(output_path, defaults['backgrounds'])
    if not os.path.isdir(backgrounds_folder):
        os.mkdir(backgrounds_folder, mode=0o755)

    fig_size = 40
    factor = defaults['map_factor'] # defaults: 2 tsne, 20 umap
    xrange = [-range, range]
    yrange = [-range, range]
    zoom = fig_size / (factor * (xrange[1] - xrange[0]))

    backgrounds_path = os.path.join(backgrounds_folder, batch_id + '_' + project_name + '.png')
    images_folder_batch = os.path.join(images_folder, batch_id, defaults['inner_folder'])
    image = map_of_images(df, xrange, yrange, images_folder_batch, backgrounds_path, zoom, fig_size)

    csv_path = os.path.join(df_folder, batch_id + '_' + project_name + '.csv')
    create_csv(df, csv_path)
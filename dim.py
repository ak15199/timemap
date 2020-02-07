from matplotlib.colors import to_rgb, to_hex, hsv_to_rgb, rgb_to_hsv


def dim(hex, saturation=1, value=1):
    rgb = to_rgb(hex)
    hsv = rgb_to_hsv(rgb)
    rgb = hsv_to_rgb(
        (hsv[0], min(1, hsv[1] * saturation), min(1, hsv[2] * value)))

    return to_hex(rgb)


def bolden(color):
    return dim(color, value=1.2, saturation=1.2)


def darken(color):
    return dim(color, value=0.9, saturation=0.9)


def lighten(color):
    return dim(color, value=1.4, saturation=0.4)

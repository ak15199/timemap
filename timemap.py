from bokeh.colors.named import darkgray, gray, lavender, white
from bokeh.colors.named import firebrick as COLOR_CA
from bokeh.colors.named import goldenrod as COLOR_AR

from bokeh.io import show, output_file
from bokeh.models import Label, Legend
from bokeh.models.glyphs import Rect
from bokeh.palettes import linear_palette
from bokeh.plotting import figure

import click
from collections import OrderedDict
from colorcet import rainbow as palette
import csv

from functools import reduce
import operator
from parse import parse

import re

from dim import bolden, darken, lighten


UNITS = {
    "h": {"text": "hours", "factor": 1},
    "d": {"text": "days", "factor": 8},
    "w": {"text": "weeks", "factor": 40},
}

OVERALL_LABEL = "Overall"


def label(p, x, y, align, color, text):
    LABEL_OFFSET = 2

    x_offset = LABEL_OFFSET if align == "left" else -LABEL_OFFSET

    l = Label(
        x=x, y=y,
        x_offset=x_offset,
        text=f" {text} ",
        text_font_size=p.yaxis.major_label_text_font_size,
        text_color=white,
        text_baseline='middle', text_align=align,
        background_fill_color=color, border_line_color=darken(color),
    )

    p.add_layout(l)

    return l


def bar(p, y, offset, value, color, units, ca_threshold, ar_threshold, mask):
    HGHT_LT = 0.8
    HGHT_PT = 0.6

    lt, pt, ca, ar = value

    color_ca = COLOR_CA.to_hex() if not mask and ca <= ca_threshold else darkgray.to_hex()
    if ca > 0:
        label(p, offset + lt, y, "left", color_ca, f"{ca:.0f}%")

    color_ar = COLOR_AR.to_hex() if not mask and ar >= ar_threshold else darkgray.to_hex()
    if ar > 0:
        label(p, offset, y, "right", color_ar, f"{ar:.0f}{units}")

    p.rect(x=offset + lt / 2, y=y, width=lt, height=HGHT_LT,
           line_color=darken(color), color=lighten(color))
    p.rect(x=offset + lt - pt / 2, y=y, width=pt, height=HGHT_PT,
           line_color=darken(color), color=bolden(color))

    return lt


def legend(p):

    font_size = p.yaxis.axis_label_text_font_size

    def glyph(color):
        return p.add_glyph(Rect(
            x=0, y=0,
            fill_color=color.to_hex(),
            line_color=darken(color.to_hex())),
                           visible=False)

    l = Legend(
        items=[
            ("Long Lead-time", [glyph(COLOR_AR)]),
            ("High Error Rate", [glyph(COLOR_CA)]),
        ],
        location="bottom_right", orientation="horizontal",
        border_line_color=gray,
        title="Priority Items to Address",
        title_text_font_size=p.yaxis.major_label_text_font_size,
        label_text_font_size=p.yaxis.major_label_text_font_size
    )

    p.add_layout(l, "below")


def plotarea(title, width, height, y_range, units):
    PADDING_PERCENT = 0.2  # magic number left-right margin to accomodate labels

    p = figure(
        title=title,
        plot_height=height,
        plot_width=width,
        background_fill_color=lavender,
        border_fill_color=lighten(lavender.to_hex()),
        y_range=y_range)

    p.x_range.range_padding = PADDING_PERCENT
    p.x_range.range_padding_units = "percent"
    p.y_range.range_padding = 0.1
    p.grid.grid_line_alpha = 1.0
    p.grid.grid_line_color = white
    p.xaxis.axis_label = UNITS[units]["text"]
    p.yaxis.axis_label = None

    return p


def ptmult(size, mult):
    a = parse("{value:d}{units:w}", size)
    if a:
        units = a["units"]
    else:
        a = parse("{value:d}", size)
        units = "pt"
        if not a:
            click.echo(f"Unparsable font size: '{size}'", err=True)
            exit(1)

    return f"{a['value']*mult}{units}"


def generate(data, title, width, height, x_range, units, font_size, items):
    """
    Generate the chart
    """

    p = plotarea(title, width, height, list(reversed(data)), units)
    p.yaxis.major_label_text_font_size = font_size
    p.title.text_font_size = ptmult(font_size, 1.2)

    # Add one to items that we retrieve in determining thresholds, since the final
    # slot is going to get swallowed by the summary line
    ca_threshold = sorted(d[2] for d in data.values()
                          if d[2] > 0)[:(items + 1)][-1]
    ar_threshold = sorted(d[3] for d in data.values()
                          if d[3] > 0)[-(items + 1):][0]

    rows = len(data)
    pal = linear_palette(palette, rows)

    # If a maximum value is specified, then push out how far the x axis will go
    # this helps with apples-to-apples comparison between before and after
    # charts
    if x_range is not None:
        p.rect(x=x_range, y=0, width=1, height=1, line_alpha=0, fill_alpha=0.0)

    index = rows - 1
    offset = 0

    for key, value in data.items():
        mask = (key == OVERALL_LABEL)
        if mask:
            offset = 0

        offset = offset + bar(p, index + 0.5, offset, value,
                              pal[index], units, ca_threshold, ar_threshold, mask)
        index -= 1

    legend(p)

    show(p)


def convert(data, units):
    factor = UNITS[units]["factor"]

    return OrderedDict(
        (key, (value[0] / factor, value[1] / factor, value[2])) for key, value in data.items())


def augment(data):
    """
    Add summary/roll-up data to the chart, and calculate complete&accurate
    """
    def percent(value):
        if value[2]:
            return value[2]/100
        return 1

    data[OVERALL_LABEL] = (
        sum(item[0] for item in data.values()),
        sum(item[1] for item in data.values()),
        100*reduce(operator.mul, map(percent, data.values())),
    )

    # add something like activity ratio, (lt-pt rather than lt/pt) to
    # determine where our biggest delays are.  This is more interesting
    # than actual ar, since we don't really care about a low activity
    # ratio if lt is negligible...
    data = OrderedDict(
        (key, (*value, value[0] - value[1])) for key, value in data.items())

    return data


def load(file):
    """
    Read a CSV file with columns (task), (lead time), (process time)
    """

    data = OrderedDict()
    line = 0
    with open(file, newline='') as csvfile:
        reader = csv.reader(csvfile, delimiter=',', quotechar='|')
        for row in reader:
            line += 1
            if row[0][0] == "#":
                continue

            try:
                data[row[0]] = (int(row[1]), int(row[2]), int(row[3]))
            except IndexError:
                click.echo(f"(line {line}) Wrong number of columns: " + ",".join(row), err=True)
            except Exception as e:
                click.echo(f"(line {line}) error: " + ",".join(row), err=True)

    return data


@click.command()
@click.option("-f", "--font-size", default="10pt", type=str,
              help="Font size ('10pt')")
@click.option("-h", "--height", default=350, type=int,
              help="Figure height")
@click.option("-i", "--items", default=3, type=int,
              help="Number of worst items to highlight")
@click.option("-o", "--output", default=None, type=str,
              help="HTML output file name")
@click.option("-t", "--title", default="",
              help="Figure title")
@click.option("-u", "--units", default=list(UNITS.keys())[0],
              type=click.Choice(UNITS.keys(), case_sensitive=False),
              help=("Display units (%s)" % ", ".join(
                  ((f"{k} ({v['text']})" for k, v in UNITS.items()))
                  )))
@click.option("-w", "--width", default=800, type=int,
              help="Figure width")
@click.option("-x", "--xrange", default=None, type=int,
              help="Figure Max X value")
@click.argument("input")
def main(input, font_size, title, width, height, xrange, units, items, output):
    """Generate a HTML chart presenting timeline from a
       Value Stream Mapping exercise
    """

    if not output:
        output = re.sub(r'.csv$', '.html', input)
    output_file(output)

    data = load(input)
    data = convert(data, units)
    data = augment(data)

    generate(data, title, width, height, xrange, units, font_size, items)


if __name__ == "__main__":
    main()

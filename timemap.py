from bokeh.colors.named import darkgray, firebrick, gray, lavender, white, goldenrod
from bokeh.io import show, output_file
from bokeh.models.ranges import DataRange1d
from colorcet import rainbow as palette
from bokeh.palettes import linear_palette
from bokeh.plotting import figure
from bokeh.models import Label

from collections import OrderedDict
import click
import csv

from functools import reduce

from dim import bolden, darken, lighten


UNITS = {
  "h": {"text": "hours", "factor": 1},
  "d": {"text": "days", "factor": 8},
  "w": {"text": "weeks", "factor": 40},
}


def label(p, x, y, align, color, text):
  LABEL_SIZE = "9pt"
  LABEL_OFFSET = 2

  x_offset = LABEL_OFFSET if align=="left" else -LABEL_OFFSET
  
  l = Label(
    x=x, y=y,
    x_offset=x_offset,
    text=f" {text} ",
    text_font_size=LABEL_SIZE, text_color=white,
    text_baseline='middle', text_align=align,
    background_fill_color=color, border_line_color=darken(color),
    )
  
  p.add_layout(l)


def bar(p, y, offset, key, value, color, units, ca_threshold, ar_threshold):
  HGHT_LT = 0.8
  HGHT_PT = 0.6

  lt, pt, ca, ar = value

  color_ca = firebrick.to_hex() if ca <= ca_threshold else darkgray.to_hex()
  if ca>0:
    label(p, offset+lt, y, "left", color_ca, f"{ca:.0f}%")
    
  color_ar = goldenrod.to_hex() if ar >= ar_threshold else darkgray.to_hex()
  if ar>0:
    label(p, offset, y, "right", color_ar, f"{ar:.0f}{units}")

  p.rect(x=offset+lt/2, y=y, width=lt, height=HGHT_LT,
    line_color=darken(color), color=lighten(color))
  p.rect(x=offset+lt - pt/2, y=y, width=pt, height=HGHT_PT,
    line_color=darken(color), color=bolden(color))

  return lt
  

def generate(data, title, width, height, x_range, units):
  """
  Generate the chart
  """
  
  PADDING_PERCENT = 0.1  # left-right margin to accomodate labels

  output_file("output.html")
  
  ca_threshold = sorted(d[2] for d in data.values() if d[2]>0)[:3][-1]
  ar_threshold = sorted(d[3] for d in data.values() if d[3]>0)[-3:][0]

  rows = len(data)
  pal = linear_palette(palette, rows)
  
  p = figure(title=title, plot_height=height, plot_width=width, y_range=list(reversed(data)))
  p.x_range.range_padding = PADDING_PERCENT
  p.x_range.range_padding_units = "percent"
  p.background_fill_color = lavender
  p.grid.grid_line_alpha=1.0
  p.grid.grid_line_color = white
  p.xaxis.axis_label = UNITS[units]["text"]
  p.yaxis.axis_label = None

  # If a maximum value is specified, then push out how far the x axis will go
  # this helps with apples-to-apples comparison between before and after charts
  if x_range is not None:
    p.rect(x=x_range, y=0, width=1, height=1, fill_alpha=0.0, color=lavender)
  
  index = rows-1
  offset = 0

  for key, value in data.items():
    offset = offset + bar(p, index+0.5, offset, key, value, pal[index], units, ca_threshold, ar_threshold)
    index -= 1
  
  show(p)


def convert(data, units):
  factor = UNITS[units]["factor"]

  return OrderedDict((key, (value[0]/factor, value[1]/factor, value[2])) for key, value in data.items())
  

def augment(data):
  """
  Add summary/roll-up data to the chart, and calculate activity ratio
  """
  data["Overall"] = (
    sum(item[0] for item in data.values()),
    sum(item[1] for item in data.values()),
    reduce(
      (lambda x, y: x/y),
       map(
       (lambda x: x if x else 1),
        map((lambda x: x[2]/100), data.values()))),
  )
    
  # add activity ratio and return
  return OrderedDict((key, (*value, value[0]-value[1])) for key, value in data.items())


def load(file):
  """
  Read a CSV file with columns (task), (lead time), (process time)
  """

  data = OrderedDict()
  with open(file, newline='') as csvfile:
    reader = csv.reader(csvfile, delimiter=',', quotechar='|')
    for row in reader:
      if row[0][0] == "#" or len(row) != 4:
        pass

      try:
        data[row[0]] = (int(row[1]), int(row[2]), int(row[3]))
      except IndexError:
        print("Not enough columns: "+",".join(row))

  return data


@click.command()
@click.option("-t", "--title", default="", help="Figure title")
@click.option("-w", "--width", default=800, type=int, help="Figure width")
@click.option("-h", "--height", default=350, type=int, help="Figure height")
@click.option("-x", "--xrange", default=None, type=int, help="Figure Max X value")
@click.option("-u", "--units", default="h", type=click.Choice(["h", "d", "w"], case_sensitive=False), help="Display units (h, d, w)")
@click.argument("file")
def main(file, title, width, height, xrange, units):

  data = load(file)
  data = convert(data, units)
  data = augment(data)

  generate(data, title, width, height, xrange, units)


if __name__ == "__main__":
  main()

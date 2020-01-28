from bokeh.colors.named import darkgray, firebrick, gray, lavender, white
from bokeh.io import show, output_file
from bokeh.models.ranges import DataRange1d
from bokeh.palettes import viridis
from bokeh.plotting import figure
from bokeh.models import Label

import collections
import colorsys
import click
import csv

from functools import reduce

from matplotlib.colors import to_rgb, to_hex, hsv_to_rgb, rgb_to_hsv


def dim(hex, saturation=1, value=1):
  rgb = to_rgb(hex)
  hsv = rgb_to_hsv(rgb)
  rgb = hsv_to_rgb((hsv[0], min(1, hsv[1]*saturation), min(1, hsv[2]*value)))

  return to_hex(rgb)


def bolden(color):
  return dim(color, value=1.2, saturation=1.2)


def darken(color):
  return dim(color, value=0.9, saturation=0.9)


def lighten(color):
  return dim(color, value=1.3, saturation=0.4)


def bar(p, y, offset, key, value, color, ca_threshold):
  HGHT_LT = 0.8
  HGHT_PT = 0.6

  lt, pt, ca = value

  if key == "Overall":
    text = [f"{100/lt*pt:.2f}% Efficiency"]
    p.rect(x=lt/2, y=y, width=lt, height=HGHT_LT, fill_alpha=0.4, color=color)
    p.rect(x=lt-pt/2, y=y, width=pt, height=HGHT_PT, color=color)
    p.text(x=lt-pt/2, y=y, text=text, text_color=white.to_hex(), text_baseline="middle")
  elif lt:
    color_ca = firebrick.to_hex() if ca <= ca_threshold else darkgray.to_hex()
    if ca>0:
      p.rect(x=offset+lt+30, y=y, width=60, height=0.8, color=color_ca, line_color=darken(color_ca))
      j = p.text(x=offset+lt+5, y=y, text=[str(ca)], text_color="#ffffff", text_baseline="middle")
    p.rect(x=offset+lt/2, y=y, width=lt, height=HGHT_LT, line_color=darken(color), color=lighten(color))
    p.rect(x=offset+lt - pt/2, y=y, width=pt, height=HGHT_PT, line_color=darken(color), color=bolden(color))

  return lt
  

def generate(data, title="Figure", width=1000, height=350, x_range=None):
  
  output_file("output.html")
  
  data["Overall"] = (
    sum(item[0] for item in data.values()),
    sum(item[1] for item in data.values()),
    reduce(
      (lambda x, y: x/y),
       map(
       (lambda x: x if x else 1),
        map((lambda x: x[2]/100), data.values())))
  )
  
  ca_threshold = sorted(d[2] for d in data.values() if d[2]>0)[:3][-1]
  rows = len(data)
  pal = viridis(rows)
  
  p = figure(title=title, plot_height=height, plot_width=width, y_range=list(reversed(data)))
  p.x_range.range_padding = 0
  p.background_fill_color = lavender
  p.grid.grid_line_alpha=1.0
  p.grid.grid_line_color = "white"
  p.xaxis.axis_label = 'hours'
  p.yaxis.axis_label = None

  # If a maximum value is specified, then push out how far autoscaling will go
  if x_range is not None:
    p.rect(x=x_range, y=0, width=1, height=1, fill_alpha=0.0, color=lavender)
  
  index = rows-1
  offset = 0

  for key, value in data.items():
    offset = offset + bar(p, index+0.5, offset, key, value, pal[index], ca_threshold)
    index -= 1
  
  show(p)


@click.command()
@click.option('-t', '--title', default="", help='Figure Title')
@click.option('-w', '--width', default=800, type=int, help='Figure Width')
@click.option('-h', '--height', default=350, type=int, help='Figure Height')
@click.option('-x', '--xrange', default=None, type=int, help='Figure Max X Value')
@click.argument('file')
def main(file, title, width, height, xrange):
  """
  Read a CSV file with columns (task), (lead time), (process time), and
  generate a chart in a web browser to represent the timeline.
  """

  data = collections.OrderedDict()
  with open(file, newline='') as csvfile:
    reader = csv.reader(csvfile, delimiter=',', quotechar='|')
    for row in reader:
      if row[0][0] == "#" or len(row) != 4:
        pass

      try:
        data[row[0]] = (int(row[1]), int(row[2]), int(row[3]))
      except IndexError:
        print("Not enough columns: "+",".join(row))

  generate(data, title, width, height, xrange)


if __name__ == "__main__":
  main()

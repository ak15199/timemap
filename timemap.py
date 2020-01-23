from bokeh.io import show, output_file
from bokeh.models.ranges import DataRange1d
from bokeh.palettes import viridis
from bokeh.plotting import figure
from bokeh.models import Label

import collections
import click
import csv


HGHT_LT = 0.6
HGHT_PT = 0.4
COLOR_BG = "#EAEAF2"

def generate(data, title="Figure", width=1000, height=350, x_range=None):
  
  output_file("output.html")
  
  data["Total"] = (
    sum(item[0] for item in data.values()),
    sum(item[1] for item in data.values())
  )
  
  rows = len(data)
  pal = viridis(rows)
  
  p = figure(title=title, plot_height=height, plot_width=width, y_range=list(reversed(data)))
  p.x_range.range_padding = 0
  p.background_fill_color = COLOR_BG
  p.grid.grid_line_alpha=1.0
  p.grid.grid_line_color = "white"
  p.xaxis.axis_label = 'hours'
  p.yaxis.axis_label = None

  # If a maximum value is specified, then push out how far autoscaling will go
  if x_range is not None:
    p.rect(x=x_range, y=0, width=1, height=1, fill_alpha=0.0, color=COLOR_BG)
  
  index = rows-1
  offset = 0

  for k, v in data.items():
    lt, pt = v
    y = index+0.5
    if k == "Total":
      text = [f"{100/lt*pt:.2f}% Efficiency"]
      p.rect(x=lt/2, y=y, width=lt, height=HGHT_LT, fill_alpha=0.4, color=pal[index])
      p.rect(x=lt-pt/2, y=y, width=pt, height=HGHT_PT, color=pal[index])
      p.text(x=lt-pt/2, y=y, text=text, text_color="#ffffff", text_baseline="middle")
    else:
      p.rect(x=offset+lt/2, y=y, width=lt, height=HGHT_LT, fill_alpha=0.4, color=pal[index])
      p.rect(x=offset+lt - pt/2, y=y, width=pt, height=HGHT_PT, color=pal[index])
  
    index -= 1
    offset = offset + lt
  
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
      print(row)
      data[row[0]] = (int(row[1]), int(row[2]))

  generate(data, title, width, height, xrange)


if __name__ == "__main__":
  main()

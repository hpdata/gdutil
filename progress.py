"""
Download a list of files from Google Drive.
"""

import progressbar
from progressbar import widgets, utils


UnknownLength = progressbar.UnknownLength


class ResumableBar(progressbar.ProgressBar):
    '''
    A progress bar with sensible defaults for downloads etc.
    This assumes that the values its given are numbers of bytes.
    '''
    # Base class defaults to 100, but that makes no sense here
    _DEFAULT_MAXVAL = progressbar.base.UnknownLength

    def __init__(self, min_value=0, max_value=None, widgets=None,
                 left_justify=True, initial_value=0, poll_interval=None,
                 widget_kwargs=None, **kwargs):
        progressbar.ProgressBar.__init__(self, min_value, max_value, widgets,
                                         left_justify, initial_value, poll_interval,
                                         widget_kwargs, **kwargs)
        self.initial_value = initial_value

    def default_widgets(self):
        if self.max_value:
            return [
                widgets.Percentage(**self.widget_kwargs),
                ' of ', widgets.SimpleProgress(
                    format='(%s)' % widgets.SimpleProgress.DEFAULT_FORMAT,
                    **self.widget_kwargs),
                ' ', widgets.Bar(**self.widget_kwargs),
                ' ', widgets.Timer(**self.widget_kwargs),
                ' ', progressbar.AdaptiveETA(),
            ]
        else:
            return [
                widgets.AnimatedMarker(),
                ' ', widgets.DataSize(),
                ' ', widgets.Timer(),
            ]

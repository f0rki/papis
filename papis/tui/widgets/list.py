import re
from prompt_toolkit.application.current import get_app
from prompt_toolkit.formatted_text.html import HTML, html_escape
from prompt_toolkit.filters import Condition
from prompt_toolkit.layout.screen import Point
from prompt_toolkit.buffer import Buffer
from prompt_toolkit.layout.controls import (
    FormattedTextControl, BufferControl
)
from prompt_toolkit.widgets import HorizontalLine
from prompt_toolkit.layout.containers import (
    HSplit, Window, ConditionalContainer
)
from prompt_toolkit.filters import has_focus

import logging

logger = logging.getLogger('tui:widget:list')


class OptionsListControl(ConditionalContainer):

    def __init__(
            self,
            options,
            default_index=0,
            header_filter=lambda x: x,
            match_filter=lambda x: x
            ):

        assert(isinstance(options, list))
        assert(callable(header_filter))
        assert(callable(match_filter))
        assert(isinstance(default_index, int))

        self.search_buffer = Buffer(multiline=False)
        self.search_buffer.on_text_changed += self.update

        self.header_filter = header_filter
        self.match_filter = match_filter
        self.current_index = default_index
        self.entries_left_offset = 2

        self._options = []
        # Options are processed here also through the setter
        self.options = options
        self.cursor = Point(0, 0)

        self.content = FormattedTextControl(
            text='',
            focusable=False,
            key_bindings=None,
            get_cursor_position=lambda: self.cursor,
        )
        self.content_window = Window(
            content=self.content,
            height=None,
        )
        self.window = HSplit([
            Window(
                height=1,
                content=BufferControl(buffer=self.search_buffer)
            ),
            HorizontalLine(),
            self.content_window
        ])

        self.update()

        super(OptionsListControl, self).__init__(
            content=self.window,
            filter=has_focus(self.search_buffer)
        )

    @property
    def options(self):
        return self._options

    @options.setter
    def options(self, new_options):
        self._options = new_options
        self.process_options()

    def update_cursor(self):
        """This function updates the cursor according to the current index
        in the list.
        """
        try:
            index = self.indices.index(self.current_index)
            line = sum(
                self.options_headers_linecount[i]
                for i in self.indices[0:index]
            )
            self.cursor = Point(0, line)
        except Exception as e:
            self.cursor = Point(0, 0)

    def move_up(self):
        try:
            index = self.indices.index(self.current_index)
            index -= 1
            if index < 0:
                self.current_index = self.indices[-1]
            else:
                self.current_index = self.indices[index]
        except ValueError:
            pass

    def move_down(self):
        try:
            index = self.indices.index(self.current_index)
            index += 1
            if index >= len(self.indices):
                self.current_index = self.indices[0]
            else:
                self.current_index = self.indices[index]
        except ValueError:
            pass

    def go_top(self):
        if len(self.indices) > 0:
            self.current_index = self.indices[0]

    def go_bottom(self):
        if len(self.indices) > 0:
            self.current_index = self.indices[-1]

    def get_search_regex(self):
        cleaned_search = (
            self.search_buffer.text
            .replace('(', '\\(')
            .replace(')', '\\)')
            .replace('+', '\\+')
            .replace('[', '\\[')
            .replace(']', '\\]')
        )
        return r".*"+re.sub(r"\s+", ".*", cleaned_search)

    def update(self, *args):
        self.filter_options()
        self.refresh()

    def filter_options(self, *args):
        indices = []
        regex = self.get_search_regex()
        for index, option in enumerate(list(self.options)):
            if re.match(regex, self.options_matchers[index], re.I):
                indices += [index]
        self.indices = indices
        if len(self.indices) and self.current_index not in self.indices:
            if self.current_index < min(self.indices):
                self.current_index = self.indices[0]
            elif self.current_index > max(self.indices):
                self.current_index = max(self.indices)
            else:
                self.current_index = self.indices[0]

    def get_selection(self):
        if len(self.indices) and self.current_index is not None:
            return self.options[self.current_index]

    def refresh(self):
        self.update_cursor()
        i = self.current_index
        oldtuple = self.options_headers[i][0]
        self.options_headers[i][0] = (
            oldtuple[0],
            '>' + re.sub(r'^ ', '', oldtuple[1]),
        )
        self.content.text = sum(
            [self.options_headers[i] for i in self.indices],
            []
        )
        self.options_headers[i][0] = oldtuple
        try:
            get_app().message_toolbar.text = "{0} {1} {3} {2}".format(
                self.get_search_regex(), self.cursor,
                self.options_headers[i],
                i
            )
        except:
            pass

    def process_options(self):
        logger.debug('processing {0} options'.format(len(self.options)))
        self.options_headers_linecount = [
            len(self.header_filter(o).split('\n'))
            for o in self.options
        ]
        logger.debug('processing headers')
        self.offsets = [' ' * self.entries_left_offset for l in self.options]
        self.options_headers = []
        for o in self.options:
            prestring = re.sub(
                r'^', ' ' * self.entries_left_offset,
                re.sub(
                    r'\n', '\n' + ' ' * self.entries_left_offset,
                    self.header_filter(o)
                )
            ) + '\n'
            try:
                htmlobject = HTML(prestring).formatted_text
            except:
                logger.error(
                    'Error processing html for \n {0}'.format(prestring)
                )
                htmlobject = [ ('fg:red', prestring) ]
            self.options_headers += [htmlobject]
        logger.debug('got {0} headers'.format(len(self.options_headers)))
        logger.debug('processing matchers')
        self.options_matchers = [self.match_filter(o) for o in self.options]
        self.indices = range(len(self.options))
        logger.debug('got {0} matchers'.format(len(self.options_matchers)))

    @property
    def screen_height(self):
        return self.content.preferred_height(None, None, None)

    @property
    def displayed_lines(self):
        info = self.content_window.render_info
        if info:
            return info.displayed_lines

    @property
    def first_visible_line(self):
        info = self.content_window.render_info
        if info:
            return info.first_visible_line()

    @property
    def last_visible_line(self):
        info = self.content_window.render_info
        if info:
            return info.last_visible_line()

    @property
    def content_height(self):
        info = self.content_window.render_info
        if info:
            return info.content_height

    def scroll_down(self):
        lvl = self.last_visible_line
        ll = self.content_height
        if ll and lvl:
            if lvl + 1 < ll:
                new = lvl + 1
            else:
                new = lvl
            self.cursor = Point(0, new)

    def scroll_up(self):
        fvl = self.first_visible_line
        if fvl:
            if fvl >= 0:
                new = fvl - 1
            else:
                new = 0
            self.cursor = Point(0, new)


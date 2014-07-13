# -*- coding: utf8 -*-

# Copyright (c) 2014 Hewlett-Packard Development Company, L.P.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import functools
import os
import textwrap

import fixtures
import mock
import testtools

from git_review import cmd
from git_review.tests import utils

# Use of io.StringIO in python =< 2.7 requires all strings handled to be
# unicode. See if StringIO.StringIO is available first
try:
    import StringIO as io
except ImportError:
    import io


class ConfigTestCase(testtools.TestCase):
    """Class testing config behavior."""

    @mock.patch('git_review.cmd.LOCAL_MODE',
                mock.PropertyMock(return_value=True))
    @mock.patch('git_review.cmd.git_directories', return_value=['', 'fake'])
    @mock.patch('git_review.cmd.run_command_exc')
    def test_git_local_mode(self, run_mock, dir_mock):
        cmd.git_config_get_value('abc', 'def')
        run_mock.assert_called_once_with(
            cmd.GitConfigException,
            'git', 'config', '-f', 'fake/config', '--get', 'abc.def')

    @mock.patch('git_review.cmd.LOCAL_MODE',
                mock.PropertyMock(return_value=True))
    @mock.patch('os.path.exists', return_value=False)
    def test_gitreview_local_mode(self, exists_mock):
        cmd.Config()
        self.assertFalse(exists_mock.called)


class GitReviewConsole(testtools.TestCase, fixtures.TestWithFixtures):
    """Class for testing the console output of git-review."""

    reviews = [
        {
            'number': '1010101',
            'branch': 'master',
            'subject': 'A simple short subject'
        }, {
            'number': '9877',
            'branch': 'stable/codeword',
            'subject': 'A longer and slightly more wordy subject'
        }, {
            'number': '12345',
            'branch': 'master',
            'subject': 'A ridiculously long subject that can exceed the '
                       'normal console width, just need to ensure the '
                       'max width is short enough'
        }]

    def setUp(self):
        super(GitReviewConsole, self).setUp()
        # ensure all tests get a separate git dir to work in to avoid
        # local git config from interfering
        self.tempdir = self.useFixture(fixtures.TempDir())
        self._run_git = functools.partial(utils.run_git,
                                          chdir=self.tempdir.path)

        self.run_cmd_patcher = mock.patch('git_review.cmd.run_command_status')
        run_cmd_partial = functools.partial(
            cmd.run_command_status, GIT_WORK_TREE=self.tempdir.path,
            GIT_DIR=os.path.join(self.tempdir.path, '.git'))
        self.run_cmd_mock = self.run_cmd_patcher.start()
        self.run_cmd_mock.side_effect = run_cmd_partial

        self._run_git('init')
        self._run_git('commit', '--allow-empty', '-m "initial commit"')
        self._run_git('commit', '--allow-empty', '-m "2nd commit"')

    def tearDown(self):
        self.run_cmd_patcher.stop()
        super(GitReviewConsole, self).tearDown()

    @mock.patch('git_review.cmd.query_reviews')
    @mock.patch('git_review.cmd.get_remote_url', mock.MagicMock)
    @mock.patch('git_review.cmd._has_color', False)
    def test_list_reviews_no_blanks(self, mock_query):

        mock_query.return_value = self.reviews
        with mock.patch('sys.stdout', new_callable=io.StringIO) as output:
            cmd.list_reviews(None)
            console_output = output.getvalue().split('\n')

        wrapper = textwrap.TextWrapper(replace_whitespace=False,
                                       drop_whitespace=False)
        for text in console_output:
            for line in wrapper.wrap(text):
                self.assertEqual(line.isspace(), False,
                                 "Extra blank lines appearing between reviews"
                                 "in console output")

    @mock.patch('git_review.cmd._use_color', None)
    def test_color_output_disabled(self):
        """Test disabling of colour output color.ui defaults to enabled
        """

        # git versions < 1.8.4 default to 'color.ui' being false
        # so must be set to auto to correctly test
        self._run_git("config", "color.ui", "auto")

        self._run_git("config", "color.review", "never")
        self.assertFalse(cmd.check_use_color_output(),
                         "Failed to detect color output disabled")

    @mock.patch('git_review.cmd._use_color', None)
    def test_color_output_forced(self):
        """Test force enable of colour output when color.ui
        is defaulted to false
        """

        self._run_git("config", "color.ui", "never")

        self._run_git("config", "color.review", "always")
        self.assertTrue(cmd.check_use_color_output(),
                        "Failed to detect color output forcefully "
                        "enabled")

    @mock.patch('git_review.cmd._use_color', None)
    def test_color_output_fallback(self):
        """Test fallback to using color.ui when color.review is not
        set
        """

        self._run_git("config", "color.ui", "always")
        self.assertTrue(cmd.check_use_color_output(),
                        "Failed to use fallback to color.ui when "
                        "color.review not present")

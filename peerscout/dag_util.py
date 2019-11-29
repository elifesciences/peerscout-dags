"""
by mowonibi
"""
import glob
import os
from airflow.utils.decorators import apply_defaults
from typing import Optional, Iterable, Dict, Callable
from airflow.operators.python_operator import PythonVirtualenvOperator
from contextlib import contextmanager
from tempfile import mkdtemp


@contextmanager
def ReusableTemporaryDirectory(prefix):
    try:
        existing = glob.glob('/tmp/' + prefix + '*')
        if len(existing):
            name = existing[0]
        else:
            name = mkdtemp(prefix=prefix)
        yield name
    finally:
        pass


class ReusablePythonVirtualenvOperator(PythonVirtualenvOperator):
    @apply_defaults
    def __init__(
            self,
            venv_dir_to_create_or_use: str,
            python_callable: Callable,
            requirements: Optional[Iterable[str]] = None,
            python_version: Optional[str] = None,
            use_dill: bool = False,
            system_site_packages: bool = True,
            op_args: Optional[Iterable] = None,
            op_kwargs: Optional[Dict] = None,
            string_args: Optional[Iterable[str]] = None,
            templates_dict: Optional[Dict] = None,
            templates_exts: Optional[Iterable[str]] = None,
            *args,
            **kwargs
    ):
        super().__init__(
            python_callable=python_callable,
            requirements=requirements,
            python_version=python_version,
            use_dill=use_dill,
            system_site_packages=system_site_packages,
            op_args=op_args,
            op_kwargs=op_kwargs,
            string_args=string_args,
            templates_dict=templates_dict,
            templates_exts=templates_exts,
            *args,
            **kwargs
        )
        self.venv_dir_to_create_or_use = venv_dir_to_create_or_use

    def execute_callable(self):
        with ReusableTemporaryDirectory(
                prefix=self.venv_dir_to_create_or_use
        ) as tmp_dir:
            if self.templates_dict:
                self.op_kwargs['templates_dict'] = self.templates_dict
            # generate filenames
            input_filename = os.path.join(tmp_dir, 'script.in')
            output_filename = os.path.join(tmp_dir, 'script.out')
            string_args_filename = os.path.join(tmp_dir, 'string_args.txt')
            script_filename = os.path.join(tmp_dir, 'script.py')

            # set up virtualenv
            self._execute_in_subprocess(self._generate_virtualenv_cmd(tmp_dir))
            cmd = self._generate_pip_install_cmd(tmp_dir)
            if cmd:
                self._execute_in_subprocess(cmd)

            self._write_args(input_filename)
            self._write_script(script_filename)
            self._write_string_args(string_args_filename)

            # execute command in virtualenv
            self._execute_in_subprocess(
                self._generate_python_cmd(tmp_dir,
                                          script_filename,
                                          input_filename,
                                          output_filename,
                                          string_args_filename))
            return self._read_result(output_filename)

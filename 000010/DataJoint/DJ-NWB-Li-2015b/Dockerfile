FROM datajoint/jupyter:python3.6

RUN pip uninstall -y datajoint
RUN pip install datajoint --pre
RUN pip install pynwb
ADD . /src/li2015b
RUN pip install -e /src/li2015b

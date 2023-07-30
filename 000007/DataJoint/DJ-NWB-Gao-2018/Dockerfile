FROM datajoint/jupyter:python3.6

RUN pip uninstall -y datajoint
RUN pip install datajoint --pre

RUN pip install pynwb

ADD . /src/gao2018

RUN pip install -e /src/gao2018


FROM datajoint/jupyter:python3.6

RUN pip uninstall -y datajoint
RUN pip install datajoint --pre
RUN pip install pynwb
RUN pip install researchpy
ADD . /src/chen2017
RUN pip install -e /src/chen2017

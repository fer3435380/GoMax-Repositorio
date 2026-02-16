FROM odoo:18.0

COPY ./requirements.txt /opt/requirements.txt

SHELL ["/bin/bash", "-xo", "pipefail", "-c"]
USER root

RUN apt-get update -y && apt-get install -y \
    build-essential \
    python3-dev \
    libreoffice \
    && ln -s /usr/bin/soffice /usr/bin/libreoffice || true \
    && rm -rf /var/lib/apt/lists/*

RUN pip install -r /opt/requirements.txt --break-system-packages

EXPOSE 8069 8071 8072

USER odoo   

ENTRYPOINT ["/entrypoint.sh"]
CMD ["odoo"]

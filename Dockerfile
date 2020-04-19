FROM javert899/pm4py
COPY . /app
WORKDIR /app
RUN mkdir dataFile
RUN pip install -r requirements.txt 
EXPOSE 5001 
ENTRYPOINT [ "python3" ] 
CMD [ "app.py" ] 
import os
from flask import Flask, request, flash, request, redirect, url_for,jsonify
from werkzeug.utils import secure_filename
from flask_cors import cross_origin

# pm4py import 
from pm4py.objects.log.importer.xes import factory as xes_import_factory
from pm4py.objects.log.importer.csv import factory as csv_importer
from pm4py.objects.conversion.log import factory as conversion_factory
from pm4py.objects.petri.petrinet import PetriNet, Marking
from pm4py.objects.petri import utils
from pm4py.objects.petri.exporter import pnml as pnml_exporter
from pm4py.algo.discovery.dfg import factory as dfg_factory
from pm4py.objects.conversion.dfg import factory as dfg_mining_factory
from pm4py.visualization.petrinet import factory as pn_vis_factory
from pm4py.algo.conformance.alignments import factory as align_factory


UPLOAD_FOLDER = '/app/dataFile/'
ALLOWED_EXTENSIONS = {'xes','csv'}

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# utils 
def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def isValidRequest(req_data):
        if req_data is None : 
            return False,None
        else:
            if ({'fileName','path'} <= set(req_data)):
                return True, req_data['fileName'].rsplit('.', 1)[1].lower()
                # if allowed_file(req_data['fileName']): 
                #     return True, req_data['fileName'].filename.rsplit('.', 1)[1].lower()
            return False ,None

# apis
@app.route('/file', methods=['GET', 'POST'])
@cross_origin()
def upload_file():
    if request.method == 'POST':
        # check if the post request has the file part
        print(request.files)
        if 'file' not in request.files:
            flash('No file part')
            return redirect(request.url)
        file = request.files['file']

        # if user does not select file, browser also
        # submit an empty part without filename
        if file.filename == '':
            flash('No selected file')
            print("error 1")
            return redirect(request.url)
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))            
            return "File has been uploaded",200
    return '''
    <!doctype html>
    <title>Upload new File</title>
    <h1>Upload new File</h1>
    <form method=post enctype=multipart/form-data>
      <input type=file name=file>
      <input type=submit value=Upload>
    </form>
    '''

@app.route('/fileInfo', methods=['GET'])
@cross_origin()
def getFileInfo():
    path = app.config['UPLOAD_FOLDER']

    files = []
    # r=root, d=directories, f = files
    for r, d, f in os.walk(path):
        for file in f:
            print(d)
            if file.rsplit('.', 1)[len(file.rsplit('.', 1)) -1] in ALLOWED_EXTENSIONS:
                files.append({"fileName":file,"path":os.path.join(r, file)})
    resp ={'files':files}
    return jsonify(resp),200


# pm4py functionality
@app.route('/getEventInfo', methods=['POST'])
@cross_origin()
def getEventInfo():
    try:
    #get payload
        log = None
        req_data = request.get_json()
        print("this")
        isValid,fileExtention = isValidRequest(req_data)
        print(req_data)
        if(not isValid ):
            return "Invalid Payload", 400
        if(fileExtention == 'xes'):
            print('[INFO] import xes file')
            log = xes_import_factory.apply(os.path.join(req_data['path']))
        elif(fileExtention == 'csv'):
            print('[INFO] import csv file')
            event_stream = csv_importer.import_event_stream(os.path.join(req_data['path']))
            print(event_stream)
            log = conversion_factory.apply(event_stream)
            print("log file ---------------")
            print(log)
        else:
            print('[ERROR] invalid file type')
            return "error occur",400
        log_dic=[]
        statistics_Graph01 =[]
        Total_Events_Count =0
        Total_Case_Count =0
        Originator = set()
        Event_Type= set()
        for case_index, case in enumerate(log):
            # print("\n case index: %d  case id: %s" % (case_index, case.attributes["concept:name"]))
            current_case ={
                "attributes": { 
                    "concept:name": case.attributes["concept:name"], 
                    "creator": case.attributes["creator"]
                }, 
                "events":[]
            }
            i =0 
            for event_index, event in enumerate(case):
                # print("event index: %d  event activity: %s" % (event_index, event["concept:name"]))
                current_event={
                    'concept:name':event["concept:name"],
                    'org:resource': event["org:resource"],
                    'Activity': event["Activity"],
                    'Resource': event["Resource"],
                    'Costs': event["Costs"]
                }
                Event_Type.add(event["concept:name"])
                Originator.add(event["org:resource"])
                current_case['events'].append(current_event)
                i+=1
            Total_Case_Count+=1
            Total_Events_Count+=i
            
            stat= { "label": "case "+str(case_index), "y": i }
            statistics_Graph01.append(stat);
        log_dic.append(current_case)
        # log = xes_import_factory.apply('running-example-just-two-cases.xes')
        dfg = dfg_factory.apply(log)
        net, im, fm = dfg_mining_factory.apply(dfg)
        alignments = align_factory.apply(log, net, im, fm)
        parameters = {"format":"svg"}
        gviz = pn_vis_factory.apply(net, im, fm, parameters=parameters)
        # pn_vis_factory.view(gviz)
        resp ={
            'Total_Case_Count':Total_Case_Count,
            'Total_Events_Count':Total_Events_Count,
            'Event_Type_Count':len(Event_Type),
            'Originator_Count':len(Originator),
            'eventStrem':log_dic,
            'graph': str(gviz),
            'statGraph01':statistics_Graph01
        }
        return resp,200
    except FileNotFoundError:
        return {"Error":"File Not Found."},400
    except:
        return {"Error":"Unexpected Error."},400


if __name__ == '__main__':
    app.run(host ='0.0.0.0', port = 5001, debug = True)  
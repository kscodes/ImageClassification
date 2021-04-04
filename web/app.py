from flask import Flask,jsonify, request
from flask_restful import Api,Resource
from pymongo import MongoClient
import bcrypt
import requests
import subprocess
import json

app = Flask(__name__)
api = Api(app)

client = MongoClient('mongodb://db:27017')
db = client.ImageRecognition #ImageRecognition
users=db['Users']

def isPresentUser(username):
    if users.find({"Username" : username}).count() == 0 :
        return False
    else:
        return True



class Register(Resource):
    def post(self):
        postedData = request.get_json()

        username = postedData["username"]
        password = postedData["password"]

        if isPresentUser(username):
            retDict = {
                "status" : 301,
                "msg" : "Invalid Username"
            }
            return jsonify(retDict)

        hashed_pw = bcrypt.hashpw(password.encode('utf8'),bcrypt.gensalt())

        users.insert({
            "Username":username,
            "Password": hashed_pw,
            "Tokens" : 6
        })

        retDict = {
            "status" : 200,
            "msg" : "Signup Succesful"
        }

        return jsonify(retDict)

def verifyPw(username,password):
    hashed_pw = users.find({
        "Username" : username
    })[0]["Password"]

    if bcrypt.hashpw(password.encode('utf8'),hashed_pw)==hashed_pw:
        return True
    else:
        return False

def backDict(status,msg):
    retMap = {
        "status" : status,
        "msg" : msg
    }
    return retMap


def chkCredentials(username,password):
    if not isPresentUser(username):
        return backDict(301, "Invalid Username"), True

    correct_pw = verifyPw(username,password)
    if not correct_pw:
        return backDict(302, "Invalid Password"), True

    return None, False


def countTokens(username):
    return users.find({
        "Username":username
    })[0]["Tokens"]

class Classify(Resource):
    def post(self):
        postedData = request.get_json()

        username = postedData['username']
        password = postedData['password']
        url = postedData['url']

        retJson, error = chkCredentials(username,password)
        if error :
            return jsonify(retJson)

        tokens = users.find({
            "Username" : username
        })[0]["Tokens"]

        if tokens<=0:
                return jsonify(backDict(303,"Insufficient Tokens"))

        r = requests.get(url)
        retJson = {}
        with open("temp.jpg","wb") as f:
            f.write(r.content)
            proc = subprocess.Popen('python classify_image.py --model_dir=. --image_file=./temp.jpg')
            proc.communicate()[0]
            proc.wait()
            with open("text.txt") as g:
                retJson = json.load(g)

        users.update({
            "Username" : username
        },{
            "$set":{
                "Tokens":tokens-1
            }
        })
        return retJson

class Refill(Resource):
    def post(self):
        postedData = request.get_json()

        username = postedData['username']
        password = postedData['admin_passwd']
        refill_amt = postedData['refill_amt']

        if not isPresentUser(username):
            return jsonify(backDict(301, "Invalid Username"))

        correct_pw = "911jacob"
        if not password == correct_pw:
            return jsonify(backDict(304, "Invalid Administrator Password"))

        curr_tokens = countTokens(username)
        users.update({
            "Username" : username
        },{
            "$set" : {
                "Tokens" : curr_tokens + refill_amt
            }
        })

        return jsonify(backDict(200, "Refill succesful"))

api.add_resource(Register,'/register')
api.add_resource(Classify,'/classify')
api.add_resource(Refill,'/refill')

if __name__=="__main__":
    app.run(host='0.0.0.0')

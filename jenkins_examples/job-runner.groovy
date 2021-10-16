import hudson.model.*

// Json support
import com.google.gson.Gson
import com.google.gson.GsonBuilder


String stageName = ""

Map payload = [:]
Map payload_data = [:]



chuckNorris()
ansiColor('xterm') {
    timestamps {
        node("master") {
            ws("workspace/${JOB_NAME}/${BUILD_NUMBER}") {
// ******************************************************************************************************
                stageName = "EmptyStep"
                stage(stageName) {
                    logInfo("Starting stage: " + stageName)
                    logOK("Finishing stage: " + stageName)
                } //stage
// ******************************************************************************************************
                stageName = "Load payload"
                stage(stageName) {
                    logInfo("Starting stage: " + stageName)
                    payload = readJSON  text: params.PAYLOAD
                    // we can't use test param so we saved data in file and passed file name
                    payload_data = readJSON file: payload["payload_file"]
                    logDebug(jsonToStringPrettyPrint(payload))
                    logDebug(jsonToStringPrettyPrint(payload_data))
                    logOK("Finishing stage: " + stageName)
                } //stage
// ******************************************************************************************************
                stageName = "Set Build Name"
                stage(stageName) {
                    logInfo("Starting stage: " + stageName)
                    currentBuild.displayName = "#${BUILD_NUMBER} \n " +
                            " Git:: " + payload_data["repository"]["html_url"] +
                            " User: " + payload_data["sender"]["login"]
                    logOK("Finishing stage: " + stageName)
                } //stage
// *********************************************************************************************************************************************************
            }
        }
    }
}

def jsonToStringPrettyPrint(parameters) {
    // convert json to readable format
    // Requires the following imports:
    // import hudson.model.*
    // import com.google.gson.Gson
    // import com.google.gson.GsonBuilder
    GsonBuilder gsonBuilder = new GsonBuilder();
    Gson prettyGson = new GsonBuilder().serializeNulls().setPrettyPrinting().create();
    String JSONObject = prettyGson.toJson(parameters);
    return JSONObject
}
def printMsg(msg, color = false) {
    colors = [
            'red'   : '\u001B[31m',
            'black' : '\u001B[30m',
            'green' : '\u001B[32m',
            'yellow': '\u001B[33m',
            'blue'  : '\u001B[34m',
            'purple': '\u001B[35m',
            'cyan'  : '\u001B[36m',
            'white' : '\u001B[37m',
            'reset' : '\u001B[0m'
    ]
    if (color != false) {
        print "${colors[color]}${msg}${colors.reset}"
    } else {
        print "[${level}] ${msg}"
    }
}

void logDebug(def msg) {
    printMsg(msg.toString(), 'purple')
}

void logOK(def msg) {
    printMsg(msg.toString(), 'green')
}

void logErr(def msg) {
    printMsg(msg.toString(), 'red')
}

void logInfo(def msg) {
    printMsg(msg.toString(), 'blue')
}

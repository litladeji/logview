#!/usr/bin/env python3
# coding: utf-8

# In[ ]:

#this script was originally written by Alex Campbell for use on the ECON-T tests: https://github.com/SC990987/MongoDBScripts
#I have modified it to upload via django instead of pymongo - it also now splits the data into seperate 'card' and 'test' documents for faster retrieval of commonly accessed 'summary' variables

import numpy as np
import glob
import json
import django

from django.conf import settings
import os


# Setup Django environment
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "logview.settings")
django.setup()

from cm_db.models import Test, Overall_Summary, CM_Card

## Grab JSON Files
idir = "imports"   #changed the origninal directory
odir = "media/logs"
fnames = sorted([
    os.path.join(idir,f)
    for f in os.listdir(idir)
    if f.startswith("report") and f.endswith(".json")
])

def stringReplace(word):
    if "[" in word:
        word = word.replace("[","_")
    if ".." in word:
        word = word.replace("..","_")
    if "/" in word:
        word = word.replace("/","_")
    if "]" in word:
        word = word.replace("]", "")
    return word

def get_Barcode(data):
    null_chip_ID = "MissingID"
    if 'chip_number' in data and data['chip_number']:
        barcode = data['chip_number']
    else:
        barcode = null_chip_ID
    return barcode

def Metadata_Formatter(metadata, metadata_type):
    #print("formatting metadata of type", metadata_type)
    if metadata_type in ["eRX_errcounts", "eTX_errcounts", "eTX_bitcounts", "eTX_delays"]:
        #print("metadata type approved!")
        if metadata_type in metadata:
            #print("metadata located in input!")
            old_list = metadata[metadata_type]
            new_list = np.array(old_list)
            serialized = new_list.tobytes()
            return serialized
        else:
            return
    else:
        print("ERROR! metadata type", metadata_type, "unknown.")

def Create_Fresh_Card(data, fname):
    newcard = CM_Card.objects.create()
    newcard.barcode = get_Barcode(data)
    blanksummary = {"total":0,"passed":0,"error":0,"failed":0,"banner":0,"css":0}
    newcard.summary = blanksummary
    #save test outcomes
    test_outcomes = []
    for test in data['tests']:
        test_outcome_temp = {"test_name":f"{stringReplace(test['nodeid'].split('::')[1])}", "passed":0, "total":1, "failed":0, "anyFailed":0, "anyForced":0, "result":"Incomplete"}
        result = test['outcome']
        newcard.summary['total'] += 1
        if result == "Passed":
            newcard.summary['passed'] += 1
            test_outcome_temp['passed'] = 1
            test_outcome_temp["result"] = "Passed"
        elif result == "Failed":
            newcard.summary['failed'] += 1
            test_outcome_temp["result"] = "Failed"
            test_outcome_temp["anyFailed"] = 1
            test_outcome_temp["failed"] = 1
        elif result == "Error":
            newcard.summary['error'] += 1
            test_outcome_temp["result"] = "Error"
        #if result == -1:
            #test_outcome_temp["result"] = "Forced"
            #test_outcome_temp["anyForced"] = 1
        test_outcomes.append(test_outcome_temp)
    for test in test_outcomes:  #elifs should improve its perfromance
        result = test["result"]
        if result == "Passed":
            test["get_css_class"] = "okay"
        if result == "Forced":
            test["get_css_class"] = "forced"
        if result == "Failed":
            test["get_css_class"] = "bad"
        if result == "Error" or result == "Incomplete":
            test["get_css_class"] = "warn"
    #TEMP BANDAID FIX BECAUSE I DO NOT YET KNOW WHICH TESTS ARE REQUIRED

    # is there really need for seperating each of this for statements
    for test in test_outcomes:
        test["required"] = 1
    for test in test_outcomes:
        date = fname[62:][:10]
        test["most_recent_date"] = date
    newcard.test_outcomes = test_outcomes
    #save test details
    newcard.save()
    overall = list(Overall_Summary.objects.all())[0]
    print("Type of totalcards:", type(overall.totalcards))
    print("Value of totalcards:", overall.totalcards)
    
    if not overall.totalcards:
        overall.totalcards = 1
    else:
        overall.totalcards +=1
    overall.save()

def Update_Existing_Card(data, fname):
    barcode = get_Barcode(data)
    oldcard = CM_Card.objects.filter(barcode = barcode)[0]
    #id assignment is easy. Just leave it as is
    old_test_outcomes = oldcard.test_outcomes
    test_outcomes = []
    for test in data['tests']:
        test_name = f"{stringReplace(test['nodeid'].split('::')[1])}"
        result = test['outcome']
        new = True
        #nesting a for loop here is very slow. There's likely a clever workaround using faster pymongo querying but for now this is a working solution.
        for test in old_test_outcomes:
            if test["test_name"] == test_name:
                new = False
                test_outcome_new = test
                test_outcome_new["total"] = str(int(test_outcome_new["total"])+1)
                if result == "Passed":
                    test_outcome_new["passed"] = str(int(test_outcome_new["passed"])+1)
                    if test["passed"] == test["total"]:
                        test_outcome_new["result"] = "Passed"
                elif result == "Failed":
                    if test["anyForced"] != 1:
                        test_outcome_new["result"] = "Failed"
                    test_outcome_new["anyFailed"] = 1
                    test_outcome_new["failed"] = str(int(test_outcome_new["failed"])+1)
                    #print(test_outcome_new["failed"])
                elif result == "Error":
                    if test["passed"] != test["total"]:
                        test_outcome_new["result"] = "Error"
                    #test_outcome_new["result"] = "Forced"
                    #test_outcome_new["anyForced"] = 1
                test_outcomes.append(test_outcome_new)
                pass
        if new:
            test_outcome_new = {"test_name":test_name, "passed":0, "total":1, "failed":0, "anyForced":0, "anyFailed":0, "result":"Incomplete"}
            if result == 1:
                test_outcome_new["passed"] = 1
                test_outcome_new["result"] = "Passed"
            elif result == 0:
                test_outcome_new["result"] = "Failed"
                test_outcome_new["anyFailed"] = 1
                test_outcome_new["failed"] = 1
            #if result == -1:
                #test_outcome_new["result"] = "Forced"
                #test_outcome_new["anyForced"] = 1
            test_outcomes.append(test_outcome_new)
    for test in test_outcomes:
        result = test["result"]
        if result == "Passed":
            test["get_css_class"] = "okay"
        elif result == "Forced":
            test["get_css_class"] = "forced"
        elif result == "Failed":
            test["get_css_class"] = "bad"
        elif result == "Incomplete":
            test["get_css_class"] = "warn"
    overall = list(Overall_Summary.objects.all())[0]
    for test in test_outcomes:
        for Test_Type in overall.test_types:
            if Test_Type["test_name"] == test["test_name"]:
                Test_Type["number_total"] += 1
                if result == "Passed":
                    Test_Type["number_passed"] += 1
                elif result == "Failed":
                    Test_Type ["number_failed"] += 1
    overall.save()

    #TEMP BANDAID FIX BECAUSE I DO NOT YET KNOW WHICH TESTS ARE REQUIRED
    for test in test_outcomes:
        test["required"] = 1
    for test in test_outcomes:
        date = fname[62:][:10]
        test["most_recent_date"] = date
    oldcard.test_outcomes = test_outcomes
    #save test details

    oldcard.save()


def UploadTests(data, fname):
    barcode = get_Barcode(data)
    for i, test in enumerate(data['tests']):# 3 there's no need for i which should give the index of the element in the list
        new_test = Test.objects.create()
        new_test.test_name = f"{stringReplace(test['nodeid'].split('::')[1])}"
        overall = list(Overall_Summary.objects.all())[0]
        isactuallynew = True # 2 would defining it here be the best or using an else below
        for test_category in overall.test_types:
            if test_category["test_name"] == new_test.test_name:
                isactuallynew = False # 2
                test_category["number_total"] += 1
                if test["outcome"] == "passed":
                    test_category["number_passed"] += 1
                elif test["outcome"] == "failed":
                    test_category["number_failed"] += 1
                new_test.required = test_category["required"]
        if isactuallynew:
            print("New Test Type detected! (",new_test.test_name,"). Added to test categories.")
            new_test_category = {"test_name":new_test.test_name, "number_passed":0, "number_failed":0, "number_total":1}
            if test["outcome"] == "passed":
                new_test_category["number_passed"] += 1
            elif test["outcome"] == "failed":
                new_test_category["number_failed"] += 1
            new_test.required = True
            new_test_category["required"] = new_test.required
            overall.test_types.append(new_test_category)
        overall.save()
        new_test.barcode = barcode
        short_fname =f"{fname}".replace(f"{idir}/","") # 7 the use of formatted string here is unecessary
        #print(short_fname)
        date = str(short_fname[12:][:10])
        hour = int(short_fname[23:][:2])
        minute = str(int(short_fname[26:][:2]))
        if minute == '0':
            minute = '00'
        if hour > 12:
            time = date + ": " + str(hour % 12) + ":" + minute + " PM"
        else:
            time = date + ": " + str(hour) + ":" + minute + " AM"
        new_test.date_run = time
        new_test.outcome = test['outcome']

        if 'metadata' in test: # 4 instead of using multiple if statements we could use get and make a default in it 
            #print(test['metadata'])
            if "eRX_errcounts" in test['metadata']:
                new_test.eRX_errcounts = Metadata_Formatter(test['metadata'], "eRX_errcounts")
            else:
                new_test.eRX_errcounts = None
            if "eTX_errcounts" in test['metadata']:
                new_test.eTX_errcounts = Metadata_Formatter(test['metadata'], "eTX_errcounts")
            else:
                new_test.eTX_errcounts = None
            if "eTX_bitcounts" in test['metadata']:
                new_test.eTX_bitcounts = Metadata_Formatter(test['metadata'], "eTX_bitcounts")
            else:
                new_test.eTX_bitcounts = None
            if "eTX_delays" in test['metadata']:
                new_test.eTX_delays = Metadata_Formatter(test['metadata'], "eTX_delays")
            else:
                new_test.eTX_delays = None
            new_test.failure_information = {
                "failure_mode": test['call']['traceback'][0]['message'] if 'traceback' in test['call'] and test['call']['traceback'][0]['message'] != '' else test['call']['crash']['message'],
                "failure_cause": test['call']['crash']['message'],
                "failure_code_line": test["call"]["crash"]["lineno"],
            } if 'failed' in test['outcome'] else None
        if 'longrepr' in test['setup']:
            new_test.longrepr = test['setup']['longrepr']
        if 'call' in test:
            if 'longrepr' in test['call']:
                new_test.failurerepr = test['call']['longrepr']
            if 'stdout' in test['call']:
                new_test.stdout = test['call']['stdout']
            if 'crash' in test['call']:
                if 'path' in test['call']['crash']:
                    new_test.crashpath = test['call']['crash']['path']
                if 'message' in test['call']['crash']:
                    new_test.crashmsg = test['call']['crash']['message']
        #label test category - Econ-D, Econ-T, or Generic
        if 'ECOND' in test["keywords"]:
            new_test.ECON_TYPE = "D"
        elif 'ECONT' in test["keywords"]:
            new_test.ECON_TYPE = "T"
        #if label field not found, check against this manually written list of tests to see if it's a known Econ-D or Econ-T one.
        # 5 definitely this manual checker is very repetitive
        else:
            EconDList = [
                    "test_chip_sync_D",
                    "test_ePortRXPRBS_ECOND_1.08",
                    "test_ePortRXPRBS_ECOND_1.2",
                    "test_ePortRXPRBS_ECOND_1.32",
                    "test_eTX_delayscan_ECOND_1.08",
                    "test_eTX_delayscan_ECOND_1.2",
                    "test_eTX_delayscan_ECOND_1.32",
                    "test_eTx_PRBS7_ECOND_1.08",
                    "test_eTx_PRBS7_ECOND_1.2",
                    "test_eTX_PRBS7_ECOND_1.32",
                    "test_hard_reset_i2c_allregisters_D",
                    "test_hold_hard_reset_D",
                    "test_hold_soft_reset_D",
                    "test_rw_allregisters_D_0",
                    "test_rw_allregisters_D_255",
                    "test_soft_reset_i2c_allregisters_D",
                    "test_wrong_i2c_address_D",
                    "test_wrong_reg_address_D",
                    ]
            EconTList = [
                    "test_chip_sync_T",
                    "test_ePortRXPRBS_ECONT_1.08",
                    "test_ePortRXPRBS_ECONT_1.2",
                    "test_ePortRXPRBS_ECONT_1.32",
                    "test_eTX_delayscan_ECONT_1.08",
                    "test_eTX_delayscan_ECONT_1.2",
                    "test_eTX_delayscan_ECONT_1.32",
                    "test_hard_reset_i2c_allregisters_T",
                    "test_hold_hard_reset_T",
                    "test_hold_soft_reset_T",
                    "test_rw_allregisters_T_0",
                    "test_rw_allregisters_T_255",
                    "test_soft_reset_i2c_allregisters_T",
                    "test_wrong_i2c_address_T",
                    "test_wrong_reg_address_T",
                    ]
            if new_test.test_name in EconDList:
                new_test.ECON_TYPE = "D"
            elif new_test.test_name in EconTList:
                new_test.ECON_TYPE = "T"
            else:
                new_test.ECON_TYPE = "Generic"
        #save test metadata
        new_test.branch = data['branch']
        new_test.commit_hash = data['commit_hash']
        new_test.remote_url = data['remote_url']
        new_test.status = data['status']
        new_test.firmware_name = data['firmware_name']
        new_test.firmware_git_desc = data['firmware_git_desc']
        new_test.filename = short_fname

        new_test.save()
    print(i+1,"tests added to file of chip",barcode) # 6 I dont get the logic here

def jsonFileUploader(fname):
    ## open the JSON File
    with open(fname) as jsonfile:
        data = json.load(jsonfile)
    ## preprocess the JSON file
    barcode = get_Barcode(data)
    #check DB for existing entries of the same name. Decide whether to update existing entry or create new one
    ID_List = CM_Card.objects.values_list('barcode',flat=True)
    #print(ID_List)
    if barcode in ID_List:
        print(barcode, "already exists! Updating Entry with new data...")
        Update_Existing_Card(data, fname)
    else:
        print(barcode, "not listed in database! Creating new entry...")
        Create_Fresh_Card(data, fname)

    UploadTests(data, fname)
## upload all the JSON files in the database

def main():

    if not Overall_Summary.objects.exists():
        Overall_Summary.objects.create(
            passedcards=0,
            failedcards=0,
            totalcards=0,
            test_types=[]
        )



   
    # Nummary = Overall_Summary.objects.first()

    # if Nummary:
    #     print("Total:", Nummary.totalcards)
    #     print("Passed:", Nummary.passedcards)
    #     print("Failed:", Nummary.failedcards)
    #     print("Test Types:", )
    #     for test in Nummary.test_types:
    #         print(f" - {test['test_name']}: Passed={test['number_passed']}, Total={test['number_total']}")
    # else:
    #     print("No summary found.")

    print("starting file upload script...")
    filename_list = list(Test.objects.values_list("filename"))
    #print("FILENAME LIST:",filename_list)
    num_uploads = 0
    for i, fname in enumerate(fnames):
        short_fname = os.path.basename(fname)

        if short_fname not in filename_list:
            print("uploading file",i)
            jsonFileUploader(fname)
            #this is to prevent accidentally uploading two of the same file at once
            filename_list.append((short_fname))
            num_uploads += 1
        else: print ("file already uploaded! skipping.")
          
        print(short_fname)
        os.rename(fname, os.path.join(odir,short_fname))
    if num_uploads != 0: print("Script complete.", num_uploads,"files uploaded.")
    else:
        print("Script complete, but 0 files uploaded. Perhaps double-check the files are in the specified import directory?")
        print("IDIR:", idir)
if __name__=="__main__":
    main()
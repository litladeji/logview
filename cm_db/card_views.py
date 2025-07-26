import sqlite3
from django.shortcuts import render
from django.views import generic
import datetime
from os import listdir, path
import json
import numpy as np
#from .models import CM_Card, Tester, Test, Attempt, Location, CMShuntParams
import cm_db.custom.filters as filters
from .models import CM_Card, Test, Overall_Summary
# Create your views here.

from django.utils import timezone, dateformat
from django.http import HttpResponse, Http404
from logview.settings import MEDIA_ROOT, CACHE_DATA

def UpdateCardSummary(barcode):
    print("updating card summary")
    card = list(CM_Card.objects.filter(barcode=barcode))[0]
    #resetting global summary values to account for changes in test validity
    overall = list(Overall_Summary.objects.all())[0]
    if card.summary['banner']:
        if card.summary['banner'] == "Passed":
            overall.passedcards -= 1
        elif card.summary['banner'] == "Failed":
            overall.failedcards -= 1
    #now assigning blank summary to card
    card.summary = {'total':0,'passed':0,'error':0,'failed':0,'banner':'None','css':'null'}
    #Update Summary and Test_Outcomes values when requested
    new_test_outcomes = []
    for test in card.test_outcomes:
        test_name = test["test_name"]
        test = {'test_name':test_name, 'passed':0, 'total':0, 'failed':0, 'anyFailed':0, 'anyForced':0, 'result':'Incomplete', 'get_css_class':'warn', 'required':1, 'most_recent_date':'0'}
        matchingtests = list(Test.objects.filter(test_name=test_name,barcode=barcode))
        for realTest in matchingtests:
            if realTest.valid:
                test['total'] += 1
                if realTest.outcome == "passed":
                    test['passed'] += 1
                if realTest.outcome == "failed":
                    test['failed'] += 1
                    test['anyFailed'] = 1
            oldTestDate = int(''.join(filter(str.isdigit, test["most_recent_date"])))
            newTestDate = int(''.join(filter(str.isdigit, realTest.date_run)))
            if oldTestDate < newTestDate:
                test['most_recent_date'] = realTest.date_run
        new_test_outcomes.append(test)
    card.test_outcomes = new_test_outcomes

    for test in card.test_outcomes:
        totalrun = test['total']
        totalpassed = test['passed']
        card.summary['total'] += 1
        if totalrun == totalpassed:
            test["result"] = "Passed"
            test["get_css_class"] = "okay"
            card.summary['passed'] += 1
        elif test["anyForced"] != 0:
            forcedAny = True
            test["result"] = "Forced"
            test["get_css_class"] = "forced"
        elif test["anyFailed"] != 0:
            failedAny = True
            test["result"] = "Failed"
            test["get_css_class"] = "bad"
            card.summary['failed'] += 1
        else:
            test["result"] = "Incomplete"
            test["get_css_class"] = "warn"
    if card.summary['failed'] == 0:
        if card.summary['error'] == 0:
            if card.summary['passed'] == card.summary['total']:
                if card.summary['total'] > 0:
                    card.summary['banner'] = "Passed"
                    card.summary['css'] = "okay"
                    overall.passedcards += 1
                else:
                    card.summary['banner'] = "No Tests"
                    card.summary['css'] = "null"
            else:
                card.summary['banner'] = "Unknown Test Outcomes"
                card.summary['css'] = "warn"
        else:
            card.summary['banner'] = "Errors"
            card.summary['css'] = "warn"
    else:
        card.summary['banner'] = "Failed"
        card.summary['css'] = "bad"
        overall.failedcards += 1
    card.save()
    overall.save()

class CatalogView(generic.ListView):
    """ This displays a list of all CM cards """

    template_name = 'cm_db/catalog.html'
    context_object_name = 'barcode_list'
    #cards = CM_Card.objects.all().order_by('barcode')
    cards = CM_Card.objects.values_list("barcode",flat = True)
    for card in cards:
        UpdateCardSummary(card)
    #num_cards = len(cards)
    def get_queryset(self):
        return self.cards
    def numberCards(self):
        return len(self.cards)

# def catalog(request):
#     """ This displays a list of all CM cards """
#     cards = CM_Card.objects.values_list('barcode', flat=True).distinct()
#     count = len(cards)
#     for card in cards:
#         UpdateCardSummary(card)
#     return render(request, 'cm_db/catalog.html', {'barcode_list': cards,
#                                                       'total_count': count,
#                                                                             })


def catalog(request):
    """ This displays a list of all CM cards """
    cards = CM_Card.objects.all().order_by("barcode")
    catalog_data = []

    for card in cards:
        UpdateCardSummary(card.barcode)
        catalog_data.append({
            "barcode": card.barcode,
            "status": card.summary  # This includes banner, css, etc.
        })

    count = len(catalog_data)

    return render(request, 'cm_db/catalog.html', {
        'barcode_list': catalog_data,
        'total_count': count,
    })



def summary(request):
    """ This displays a summary of the cards """
    if CACHE_DATA:
        cache = path.join(MEDIA_ROOT, "cached_data/summary.json")
        print("opening JSON")
        infile = open(cache, "r")
        print("opened JSON")
        print("Loading JSON")
        cardStat = json.load(infile)
        print("JSON Loaded")
    else:
        print("Loading Cards")
        cards = list(CM_Card.objects.all().order_by('barcode'))
        print("Loaded Cards")
        print("Loading Tests")
        attempts = list(Test.objects.all())
        print("Loaded Tests")
        print("Loading Attempts")
        overall = list(Overall_Summary.objects.all())[0]
        tests = []
        for a in overall.test_types:
            tests.append({"name":a["test_name"],"required":a['required']})
        print("Loaded Attempts")
        print("Getting States!")
        cardStat = filters.getCardTestStates(cards, tests, attempts)
        print("Got 'em!")
        for card in cards:
            UpdateCardSummary(card.barcode)
    return render(request, 'cm_db/summary.html', {'cards': cardStat})


def calibration(request, card):
    """ This displays the calibration overview for a card """
    if len(card) > 7:
        try:
            p = CM_Card.objects.get(uid__endswith=card)
        except CM_Card.DoesNotExist:
            raise Http404("CM card with unique id " + str(card) + " does not exist")
    else:
        try:
            p = CM_Card.objects.get(barcode__endswith=card)
        except CM_Card.DoesNotExist:
            raise Http404("CM card with barcode " + str(card) + " does not exist")

    calibrations = p.CMshuntparams_set.all().order_by("group")

    return render(request, 'cm_db/calibration.html', {'card': p, 'cals': list(calibrations)})

def calResults(request, card, group):
    """ This displays the calibration results for a card """
    if len(card) > 7:
        try:
            p = CM_Card.objects.get(uid__endswith=card)
        except CM_Card.DoesNotExist:
            raise Http404("CM card with unique id " + str(card) + " does not exist")
    else:
        try:
            p = CM_Card.objects.get(barcode__endswith=card)
        except CM_Card.DoesNotExist:
            raise Http404("CM card with barcode " + str(card) + " does not exist")
    calibration = p.CMshuntparams_set.get(group=group)

    if str(calibration.results) != "default.png":
        conn = sqlite3.connect(path.join(MEDIA_ROOT, str(calibration.results)))
        c = conn.cursor()
        c.execute("select * from CMshuntparams")
        data = []
        for item in c:
            temp = { "id":str(item[0]),
                     "serial":str(p.barcode),
                     "CM":str(item[2]),
                     "capID":str(item[3]),
                     "range":str(item[4]),
                     "shunt":str(item[5]),
                     "date":str(item[7]),
                     "slope":str(item[8]),
                     "offset":str(item[9]),
                    }
            data.append(temp)
    return render(request, 'cm_db/cal_results.html', {'card': p,
                                                          'data': data,
                                                         })

def calPlots(request, card, group):
    """ This displays the calibration plots for a card """
    if len(card) > 7:
        try:
            p = CM_Card.objects.get(uid__endswith=card)
        except CM_Card.DoesNotExist:
            raise Http404("CM card with unique id " + str(card) + " does not exist")
    else:
        try:
            p = CM_Card.objects.get(barcode__endswith=card)
        except CM_Card.DoesNotExist:
            raise Http404("CM card with barcode " + str(card) + " does not exist")
    calibration = p.CMshuntparams_set.get(group=group)

    files = []

    if str(calibration.plots) != "default.png" and path.isdir(path.join(MEDIA_ROOT, str(calibration.plots))):
        for f in listdir(path.join(MEDIA_ROOT, str(calibration.plots))):
            files.append(path.join(calibration.plots.url, path.basename(f)))
    else:
        files.append("No Data!")
    return render(request, 'cm_db/cal_plots.html', {'card': p,
                                                        'plots': files,
                                                         })
class TestersView(generic.ListView):
    """ This displays the users and email addresses """

    template_name = 'cm_db/testers.html'
    context_object_name = 'tester_list'
    def get_queryset(self):
        return Tester.objects.all().order_by('username')


class TestDetailsView(generic.ListView):
    """ This displays the tests and their descriptions """

    template_name = 'cm_db/test-details.html'
    context_object_name = 'test_list'
    def get_queryset(self):
        return Test.objects.all().order_by('name')


def stats(request):
    """ This displays a summary of the cards """

    # Get required attempts and tests
    if CACHE_DATA:
        cache = path.join(MEDIA_ROOT, "cached_data/stats.json")
        infile = open(cache, "r")
        statistics = json.load(infile)
    else:
        attempts = []
        overall = list(Overall_Summary.objects.all())[0]
        tests = []
        for test in overall.test_types:
            if test["required"]:
                tests.append(test)

        for test in tests:
            relevant_runs = list(Test.objects.filter(test_name=test["test_name"]))
            attempts.extend(relevant_runs)

        cards = list(CM_Card.objects.all().order_by("barcode"))

        testFailedStats = filters.getFailedCardStats(cards, tests, attempts)
        testPassedStats = filters.getPassedCardStats(cards, tests, attempts)
        testRemStats = filters.getRemCardStates(cards, tests, attempts)
        statistics = {'passed': testPassedStats,
                      'failed': testFailedStats,
                      'remaining': testRemStats,
                     }

    return render(request, 'cm_db/stats.html', statistics)

def detail(request, card):
    #print(card)
    """ This displays the overview of tests for a card """
    try:
        #p_results = CM_Card.objects.get(barcode__endswith=card)
        p = CM_Card.objects.all().filter(barcode = card)[0]
        #print("p results:",p)
    except CM_Card.DoesNotExist:
        #raise Http404("CM card with barcode " + str(card) + " does not exist")
        return render(request, 'cm_db/error.html')
    testnames = []
    attempts = []
    status = {"total":0, "passed":0}
    test_overview = []
    failedAny = False
    forcedAny = False


    card_test_outcomes = p.test_outcomes
    '''
    attemptList = attempts[nodeid==test].order_by("attempt_number")
    if attemptList:
        last = attemptList[len(attemptList)-1]
        if not last.revoked and test.required:
            if last.overwrite_pass:
                status["passed"] += 1
                forcedAny = True
            elif last.passed_all():
                status["passed"] += 1
            else:
                failedAny = True
        attempts.append({"attempt":last, "valid": True, "required": test.required})
    else:
        attempts.append({"attempt":test.test_name, "valid": False, "required": test.required})
        '''

    status = p.summary
    if(request.POST.get('comment_add')):
        comment = ""
        if p.comments:
            comment += "\n"
        timeposted = dateformat.format(timezone.localtime(), 'Y-m-d H:i')
        comment += str(timeposted + ": " + request.POST.get('comment'))
        tempcomments = p.comments
        if not tempcomments:
            tempcomments = ""
        tempcomments += comment
        p.comments = tempcomments
        p.save()

    if(request.POST.get('location_add')):
        newloc = {"geo_loc":request.POST.get("location")}
        timeposted = dateformat.format(timezone.localtime(), 'Y-m-d H:i')
        newloc["date_received"] = timeposted
        temploc = p.locations
        if not temploc:
            temploc = []
        temploc.append(newloc)
        p.locations = temploc
        p.save()
    return render(request, 'cm_db/detail.html', {
                                                     'card': p,
                                                     'rm' : "PLACEHOLDER",
                                                     'rm_slot' : "PLACEHOLDER",
                                                     'cu' : "PLACEHOLDER",
                                                     'attempts':card_test_outcomes,
                                                     'locations':"PLACEHOLDER",
                                                     'status':status,
                                                    })

#class CatalogView(generic.ListView):
#    """ This displays a list of all CM cards """
#
#    template_name = 'cm_db/catalog.html'
#    context_object_name = 'barcode_list'
#    def get_queryset(self):
#        return CM_Card.objects.all().order_by('barcode')
#
def error(request):
    """ This displays an error for incorrect barcode or unique id """
    return render(request, 'cm_db/error.html')

class PlotView(generic.ListView):
    """ This displays various plots of data """
   #getting these plots working seems to require some understanding of javascript that i do not have the time to obtain.
   #Currently it is sending the html page a list of tuples in the form ("test_name", [all test runs of that name])
   #this seems to be a format it is unhappy with. It's also possible it is trying to read from a nonexistent prerendered file to
   #display these, as a lot of the previous site features worked like that. I have tried to minimize reliance on non-MongoDB data.
    template_name = 'cm_db/plots.html'
    context_object_name= 'tests'
    def get_queryset(self):
        tests = []
        testnames = []
        overall = list(Overall_Summary.objects.all())[0]
        for test in overall.test_types:
            testnames.append(test["test_name"])
        for test_name in testnames:
            relevant_attempts = Test.objects.filter(test_name=test_name)
            tests.append((test_name, relevant_attempts))
        return tests

def testDetail(request, card, test):
    """ This displays details about a specific test for a card """
    try:
        p = CM_Card.objects.get(barcode__endswith=card)
    except CM_Card.DoesNotExist:
        raise Http404("CM card with barcode " + str(card) + " does not exist")
    try:
        curTest = Test.objects.all().filter(test_name=test,barcode=card)
    except CM_Card.DoesNotExist:
        raise Http404("CM card does not exist")

    attemptList = list(curTest)
    #print(attemptList)
    attemptData = []
    for attempt_number, attempt in enumerate(attemptList):
        data = ""
        if not str(attempt.filename) == "default.png":

            '''
            inFile = open(path.join(MEDIA_ROOT, str(attempt.JSON_metadata["filename"])), "r")
            tempDict = json.load(inFile)
            if attempt.test_name.abbreviation == "overall pedestal" and "pedResults" in tempDict["TestOutputs"]:
                data = tempDict["TestOutputs"]["pedResults"]
            elif attempt.test_name.abbreviation == "overall charge injection" and "ciResults" in tempDict["TestOutputs"]:
                data = tempDict["TestOutputs"]["ciResults"]
            elif attempt.test_name.abbreviation == "overall phase scan" and "phaseResults" in tempDict["TestOutputs"]:
                data = tempDict["TestOutputs"]["phaseResults"]
            elif attempt.test_name.abbreviation == "overall shunt scan" and "shuntResults" in tempDict["TestOutputs"]:
                data = tempDict["TestOutputs"]["shuntResults"]
            elif "ResultStrings" in tempDict:
                if attempt.test_name.abbreviation in tempDict["ResultStrings"]:
                    data = tempDict["ResultStrings"][attempt.test_name.abbreviation]
            '''
            filename = attempt.filename
            secretlist = ['pseudo', 'pseudopod', 'myresluger']
            #Force Pass request handling
            if request.POST.get('overwrite_pass'):
                if int(request.POST.get('overwrite_pass')) == attempt_number:
                    if (request.POST.get(f'secret_{attempt_number}') in secretlist):
                        attempt.overwrite_pass = not attempt.overwrite_pass
                        attempt.save()
            #Mark Invalid request handling
            if request.POST.get('overwrite_valid'):
                if int(request.POST.get('overwrite_valid')) == attempt_number:
                    if (request.POST.get(f'secret_{attempt_number}') in secretlist):
                        attempt.valid = not attempt.valid
                        attempt.save()
            #New Comment request handling
            if(request.POST.get('comment_add')):
                if int(request.POST.get('comment_number')) == attempt_number:
                    comment = ""
                    if not attempt.comments == "":
                        comment += "\n"
                    timeposted = dateformat.format(timezone.localtime(), 'Y-m-d H:i')
                    comment += str(timeposted + " - " + request.POST.get('comment'))
                    tempcomments = attempt.comments
                    if not tempcomments:
                        tempcomments = ""
                    tempcomments += comment
                    attempt.comments = tempcomments
                    attempt.save()

            outcome = attempt.outcome
            if outcome == "passed":
                status = "passed"
                css = "okay"
            elif outcome == "failed":
                status = "FAILED"
                css = "bad"
            else:
                status = outcome
                css = "warn"
            if attempt.overwrite_pass:
                status += " - FORCED"
                css = "forced"
                if not attempt.valid:
                    status = outcome + " - INVALID - FORCE PASS OVERRIDDEN"
                    css = None
            elif not attempt.valid:
                status += " - INVALID"
                css = None
            data = {}
            data["str"] = ""
            data["str"] += "---------------------------------------\n \n"
            data["str"]+= f"Branch: {attempt.branch} \n \n"
            data["str"] += f"Commit Hash: {attempt.commit_hash} \n \n"
            data["str"] += f"Remote URL: {attempt.remote_url} \n \n"
            data["str"] += f"Status: {attempt.status} \n \n"
            data["str"]+= f"Firmware Name: {attempt.firmware_name} \n \n"
            data["str"] += f"Firmware Git Desc: {attempt.firmware_git_desc} \n \n"
            ECON_D_eRX_shape = (-1,6)
            data["ECON_D_eRX_shape"] = range(ECON_D_eRX_shape[1])
            ECON_D_eTX_shape = (-1,2)
            data["ECON_D_eTX_shape"] = range(ECON_D_eTX_shape[1])
            ECON_T_eRX_shape = (-1,12)
            data["ECON_T_eRX_shape"] = range(ECON_T_eRX_shape[1])
            ECON_T_eTX_shape = (-1,5)
            data["ECON_T_eTX_shape"] = range(ECON_T_eTX_shape[1])
            if attempt.eRX_errcounts:
                if attempt.ECON_TYPE == "D":
                    parsed_array = np.frombuffer(attempt.eRX_errcounts, dtype = int).reshape(ECON_D_eRX_shape).tolist()
                    #print(parsed_array)
                if attempt.ECON_TYPE == "T":
                    parsed_array = np.frombuffer(attempt.eRX_errcounts, dtype = int).reshape(ECON_T_eRX_shape).tolist()
                data["has_eRX_errcounts"] = True
                data["eRX_errcounts"] = parsed_array
            if attempt.eTX_errcounts:
                if attempt.ECON_TYPE == "D":
                    parsed_array = np.frombuffer(attempt.eTX_errcounts, dtype = int).reshape(ECON_D_eTX_shape).tolist()
                if attempt.ECON_TYPE == "T":
                    parsed_array = np.frombuffer(attempt.eTX_errcounts, dtype = int).reshape(ECON_T_eTX_shape).tolist()
                data["has_eTX_errcounts"] = True
                data["eTX_errcounts"] = parsed_array
            if attempt.eTX_bitcounts:
                if attempt.ECON_TYPE == "D":
                    parsed_array = np.frombuffer(attempt.eTX_bitcounts, dtype = int).reshape(ECON_D_eTX_shape).tolist()
                if attempt.ECON_TYPE == "T":
                    parsed_array = np.frombuffer(attempt.eTX_bitcounts, dtype = int).reshape(ECON_T_eTX_shape).tolist()
                data["has_eTX_bitcounts"] = True
                data["eTX_bitcounts"] = parsed_array
            if attempt.eTX_delays:
                parsed_array = np.frombuffer(attempt.eTX_delays, dtype = int).reshape(-1,1).tolist()
                data["has_eTX_delays"] = True
                data["eTX_delays"] = parsed_array
            if attempt.longrepr:
                data["has_error_report"] = True
                data["error_report"] = attempt.longrepr
            if attempt.stdout:
                data["has_stdout"] = True
                data["stdout"] = attempt.stdout
            if attempt.crashpath:
                data["has_crashpath"] = True
                data["crashpath"] = attempt.crashpath
            if attempt.crashmsg:
                data["has_crashmsg"] = True
                data["crashmsg"] = attempt.crashmsg

            '''
            -------------------
            Error Info (if applicable):
            eRX_errcounts: {{attempt.eRX_errcounts}} \n
            eTX_errcounts: {{attempt.eTX_errcounts}} \n
            eTX_bitcounts: {{attempt.eTX_bitcounts}} \n
            eTX_delays: {{attempt.eTX_delays}} \n
            '''

        attemptData.append((attempt, filename, attempt_number, status, css, data))

    return render(request, 'cm_db/testDetail.html', {'card': p,
                                                         'test': test,
                                                         'attempts': attemptData
                                                         })


def fieldView(request):
    """ This displays details about tests on a card """
    options = ["Barcode",
               "Comments",
               "Last Location",
               "Card Status",
               "No. of Tests Failed",
               "No. of Tests Run",]

    fields = []
    for i in range(5):
        if(request.POST.get('field' + str(i+1))):
            field = request.POST.get('field' + str(i+1))
            if field in options:
                fields.append(field)


    cards = list(CM_Card.objects.all().order_by("barcode"))
    items = []
    # Info for "Card Status"
    '''
    cache = path.join(MEDIA_ROOT, "cached_data/summary.json")
    infile = open(cache, "r")
    cardStat = json.load(infile)
    infile.close()
    '''
    num_required = "PLACEHOLDER"
    for i in range(len(cards)):
        card = cards[i]
        item = {}
        item["id"] = card.barcode
        item["fields"] = []
        for field in fields:
            if field == "Barcode":
                item['fields'].append(card.barcode)
            elif field == "Comments":
                item['fields'].append(card.comments)
            elif field == "Last Location":
                loc_list = card.locations
                if loc_list == None:
                    item["fields"].append("No Locations Recorded")
                elif len(loc_list) == 0:
                    item["fields"].append("No Locations Recorded")
                else:
                    #item["fields"].append(len(card.location_set.all()))
                    loc_list = sorted(loc_list, key= lambda d:d['date_received'])
                    item["fields"].append(str(loc_list[0]["geo_loc"]+ ": " + loc_list[0]['date_received']))
            elif field == "Card Status":
                item["fields"].append(card.summary["banner"])
                item["css"] = card.summary["css"]
                '''
                if cardStat["failed"] != 0:
                    item["fields"].append("FAILED")
                elif cardStat[i]["num_passed"] == num_required:
                    if cardStat["forced"]:
                        item["fields"].append("GOOD (FORCED)")
                    else:
                        item["fields"].append("GOOD")
                else:
                    item["fields"].append("INCOMPLETE")
                '''
            elif field == "No. of Tests Failed":
                item["fields"].append(card.summary["failed"])
            elif field == "No. of Tests Run":
                item["fields"].append(card.summary["total"])

            else:
                item["fields"].append(getattr(card, field))

        items.append(item)

    return render(request, 'cm_db/fieldView.html', {'fields': fields, "items": items, "options": options})
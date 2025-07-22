def attemptTotalState(attempts):
    status = "default"
    forced = False
    for attempt in attempts:
        if attempt.revoked:
            if status == "default":
                status = "incomplete"
        else:
            if not status == "failed":
                if attempt.overwrite_pass:
                    forced = True
                    status = "passed"
                elif attempt.passed_all():
                    status = "passed"
                else:
                    status = "failed"
    return (status, forced)


def getPassedDates(cards, tests, attempts):
    cardStates = getCardTestStatesDates(cards, tests, attempts)

    passedCards = []

    for card in cardStates:
        if len(card["failed"]) == 0 and len(card["remaining"]) == 0:
            passedCards.append(card["passed"][0][1])

    return passedCards

def getFailedDates(cards, tests, attempts):
    cardsToInd = {}

    for i in range(len(cards)):
        cardsToInd[cards[i].pk] = i

    cardFailed = [(False, 0)] * len(cards)
    for attempt in attempts:
        if not attempt.revoked:
            cardInd = cardsToInd[attempt.card_id]
            if not attempt.num_failed == 0:
                if cardFailed[cardInd][1] == 0:
                    cardFailed[cardInd] = (True, attempt.date_tested)
                elif cardFailed[cardInd][1] < attempt.date_tested:
                    cardFailed[cardInd] = (True, attempt.date_tested)


    failedCards = []
    for i in range(len(cards)):
        if cardFailed[i][0]:
            failedCards.append(cardFailed[i][1])

    return failedCards

def getPassedCards(cards, tests, attempts):
    cardStates = getCardTestStates(cards, tests, attempts)

    passedCards = []

    for card in cardStates:
        if len(card["failed"]) == 0 and len(card["remaining"]) == 0:
            passedCards.append(card["barcode"])

    return passedCards


def getFailedCards(cards, tests, attempts):
    cardsToInd = {}

    for i in range(len(cards)):
        cardsToInd[cards[i].pk] = i

    cardFailed = [False] * len(cards)
    for attempt in attempts:
        if not attempt.revoked:
            if not attempt.num_failed == 0:
                cardFailed[cardsToInd[attempt.card_id]] = True

    failedCards = []
    for i in range(len(cards)):
        if cardFailed[i]:
            failedCards.append(cards[i].barcode)

    return failedCards

def getCardTestStatesDates(cards, tests, attempts):
    """ This function returns an array of cards and tests based on passes or fails """
    numTests = len(tests)
    testsToInd = {}

    for i in range(numTests):
        testsToInd[tests[i].pk] = i

    state = {}

    for card in cards:
        state[card.pk] = [(0, 0)] * numTests

    for attempt in attempts:
        if not attempt.revoked:
            testInd = testsToInd[attempt.test_type_id];
            if not attempt.num_failed == 0:
                if state[attempt.card_id][testInd][1] == 0:
                    state[attempt.card_id][testInd] = (2, attempt.date_tested)
                elif state[attempt.card_id][testInd][1] < attempt.date_tested:
                    state[attempt.card_id][testInd] = (2, attempt.date_tested)
            elif not attempt.num_passed == 0 and state[attempt.card_id][testInd][0] == 0:
                if state[attempt.card_id][testInd][1] == 0:
                    state[attempt.card_id][testInd] = (1, attempt.date_tested)
                elif state[attempt.card_id][testInd][1] < attempt.date_tested:
                    state[attempt.card_id][testInd] = (1, attempt.date_tested)

    cardStat = []

    for i in range(len(cards)):
        card = cards[i]
        curFail = []
        curPass = []
        curRem = []
        tempDict = {}
        curState = state[card.pk]

        for i in range(numTests):
            if curState[i][0] == 0:
                curRem.append((tests[i].name, curState[i][1]))
            elif curState[i][0] == 1:
                curPass.append((tests[i].name, curState[i][1]))
            elif curState[i][0] == 2:
                curFail.append((tests[i].name, curState[i][1]))

        tempDict['barcode'] = card.barcode
        tempDict['failed'] = curFail
        tempDict['passed'] = curPass
        tempDict['remaining'] = curRem
        cardStat.append(tempDict)
    return cardStat

def getCardTestStates(cards, tests, attempts):
    """ This function returns an array of cards and tests based on passes or fails """
    numTests = len(tests)
    testsToInd = {}

    for i in range(numTests):
        testsToInd[tests[i]["name"]] = i

    state = {}

    for card in cards:
        state[card.barcode] = {}
        state[card.barcode]["states"] = [0] * numTests
        state[card.barcode]["forced"] = False

    for attempt in attempts:
        testInd = testsToInd[attempt.test_name]
        if attempt.valid and not state[attempt.barcode]["states"][testInd] == 2:
            if attempt.overwrite_pass:
                state[attempt.barcode]["states"][testInd] = 1
                if tests[testInd].required:
                    state[attempt.barcode]["forced"] = True
            elif attempt.outcome == "failed":
                state[attempt.barcode]["states"][testInd] = 2
            elif attempt.outcome == "passed":
                state[attempt.barcode]["states"][testInd] = 1

    cardStat = []

    for i in range(len(cards)):
        card = cards[i]
        curFail = []
        curPass = []
        curRem = []
        tempDict = {}
        tempDict["num_passed"] = 0                # number of passed required tests
        tempDict["num_failed"] = 0                # number of failed required tests
        curState = state[card.barcode]["states"]

        for j in range(numTests):
            if curState[j] == 0:
                curRem.append(tests[j]["name"])
            elif curState[j] == 1:
                curPass.append(tests[j]["name"])
                if tests[j]["required"]:
                    tempDict["num_passed"] += 1
            elif curState[j] == 2:
                curFail.append(tests[j]["name"])
                if tests[j]["required"]:
                    tempDict["num_failed"] += 1

        tempDict['barcode'] = card.barcode
        tempDict['failed'] = curFail
        tempDict['passed'] = curPass
        tempDict['remaining'] = curRem
        tempDict['forced'] = state[card.barcode]["forced"]
        cardStat.append(tempDict)
    return cardStat

def getRemCardStates(cards, tests, attempts):
    """ Returns a list of cards which need each test """
    cardStates = getCardTestStates(cards, tests, attempts)

    testStat = {}
    for test in tests:
        testStat[test["name"]] = []

    for i in range(len(cardStates)):
        barcode = cardStates[i]['barcode']
        for test in cardStates[i]['remaining']:
            testStat[test].append(barcode)

    finalStats = []
    for name in testStat:
        tempStat = {"name": name}
        tempStat["cards"] = testStat[name]
        tempStat["number"] = len(tempStat["cards"])
        tempStat["percentage"] = round( float(len(tempStat["cards"]))/len(cards) * 100, 1)
        finalStats.append(tempStat)
    return sorted(finalStats, key=lambda k: k['percentage'], reverse=True)


def getFailedCardStats(cards, tests, attempts):
    """ Returns a list of failed cards for each test """
    numCards = len(cards)
    cardsToInd = {}

    for i in range(numCards):
        cardsToInd[cards[i].barcode] = i

    failed = {}

    for test in tests:
        failed[test["test_name"]] = [False] * numCards

    for attempt in attempts:
        if attempt.valid:
            cardInd = cardsToInd[attempt.barcode]
            if attempt.outcome == "failed":
                failed[attempt.test_name][cardInd] = True

    testStat = []

    for i in range(len(tests)):
        tempStat = {"name": tests[i]["test_name"]}
        failCards = []
        for j in range(len(cards)):
            if failed[tests[i]["test_name"]][j]:
                failCards.append(cards[j].barcode)
        tempStat["cards"] = failCards
        tempStat["number"] = len(failCards)
        tempStat["percentage"] = round( float(len(failCards))/len(cards) * 100, 1)
        testStat.append(tempStat)

    return sorted(testStat, key=lambda k: k['percentage'], reverse=True)

def getPassedCardStats(cards, tests, attempts):
    """ Returns a list of cards which passed all tests """
    for test in tests:
        test["name"] = test["test_name"]
    cardStates = getCardTestStates(cards, tests, attempts)

    cardStats = {}

    cardStats["cards"] = getPassedCards(cards, tests, attempts)
    cardStats["number"] = len(cardStats["cards"])
    cardStats["percentage"] = round( float(len(cardStats["cards"]))/len(cards) * 100, 1)

    return cardStats
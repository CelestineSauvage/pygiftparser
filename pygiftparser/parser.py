#!/usr/bin/python3
#-*- coding: utf-8 -*-
import logging
import random
import re
import yattag
import uuid
import markdown
from pygiftparser import i18n
import sys

_ = i18n.language.gettext

# TODOS:
# - unittest
MARKDOWN_EXT = ['markdown.extensions.extra', 'markdown.extensions.nl2br', 'superscript']

# Url and blank lines (moodle format)
reURL=re.compile(r"(http://[^ ]+)",re.M)
reNewLine=re.compile(r'\n\n',re.M)

#WARNING MESSAGES
INVALID_FORMAT_QUESTION = "Vous avez saisi un quizz invalide"

# Sub regular expressions
ANYCHAR=r'([^\\=~#]|(\\.))'
OPTIONALFEEDBACK='(#(?P<feedback>'+ANYCHAR+'*))?'
OPTIONALFEEDBACK2='(#(?P<feedback2>'+ANYCHAR+'*))?'
GENERALFEEDBACK='(####(\[(?P<gf_markup>.*?)\])*(?P<generalfeedback>.*))?'
NUMERIC='[\d]+(\.[\d]+)?'


# Regular Expressions
reSepQuestions=re.compile(r'^\s*$')
reComment=re.compile(r'^//.*$')
reCategory=re.compile(r'^\$CATEGORY: (?P<cat>[/\w$]*)')

# Special chars
reSpecialChar=re.compile(r'\\(?P<char>[#=~:{}])')


# Heading
# Title is supposed to be at the begining of a line
reTitle=re.compile(r'^::(?P<title>.*?)::(?P<text>.*)$',re.M+re.S)
reMarkup=re.compile(r'^\s*\[(?P<markup>.*?)\](?P<text>.*)',re.M+re.S)
reAnswer=re.compile(r'^(?P<head>.*[^\\]){\s*(?P<answer>.*?[^\\]?)'+GENERALFEEDBACK+'}(?P<tail>.*)',re.M+re.S)

# numeric answers
reAnswerNumeric=re.compile(r'^#[^#]')
reAnswerNumericValue = re.compile(r'\s*(?P<value>'+NUMERIC+')(:(?P<tolerance>'+NUMERIC+'))?'+OPTIONALFEEDBACK)
reAnswerNumericInterval=re.compile(r'\s*(?P<min>'+NUMERIC+')(\.\.(?P<max>'+NUMERIC+'))'+OPTIONALFEEDBACK)
reAnswerNumericExpression = re.compile(r'\s*(?P<val1>'+NUMERIC+')((?P<op>:|\.\.)(?P<val2>'+NUMERIC+'))?'+OPTIONALFEEDBACK)

# Multiple choices only ~ symbols
reAnswerMultipleChoices = re.compile(r'\s*(?P<sign>=|~)(%(?P<fraction>-?'+NUMERIC+')%)?(?P<answer>('+ANYCHAR+')*)'+OPTIONALFEEDBACK)

# True False
reAnswerTrueFalse = re.compile(r'^\s*(?P<answer>(T(RUE)?)|(F(ALSE)?))\s*'+OPTIONALFEEDBACK+OPTIONALFEEDBACK2)

# Match (applies on 'answer' part of the reAnswerMultipleChoices pattern
reMatch = re.compile(r'(?P<question>.*)->(?P<answer>.*)')

def stripMatch(match,s):
    if match.group(s):
        return match.group(s).strip()
    else:
        return ""

def mdToHtml(text,doc):
    """
    Transform txt in markdown to html
    """
    if not (text.isspace()):
        text = re.sub(r'\\n','\n',text)
        html_text = markdown.markdown(text, MARKDOWN_EXT, output_format='xhtml')
        # html_text = utils.add_target_blank(html_text)
        doc.asis(html_text)
        doc.text(' ')

############# Sets of answers ###############
# Can be a singleton, empty or not or just the emptyset!

class AnswerSet:
    def __init__(self,question):
        self.question = question
        self.valid = True


    def myprint(self):
        print (self.__class__)

    def toEDX(self, max_att = "1"):
        doc = yattag.Doc()
        with doc.tag("problem", display_name=self.question.title, max_attempts=max_att):
            with doc.tag("legend"):
                mdToHtml(self.question.text,doc)
            self.scriptEDX(doc)
            self.ownEDX(doc)
            # FIXME : Ajouter un warning ici si rien n'est renvoyé
            if (len(self.question.generalFeedback) > 1):
                with doc.tag("solution"):
                    with doc.tag("div", klass="detailed-solution"):
                        mdToHtml(self.question.generalFeedback,doc)
        return doc.getvalue()

    def toHTML(self,doc):
        pass

    def toHTMLFB(self,doc):
        pass

    def listInteractions(self,doc,tag,text):
        pass

    def possiblesAnswersIMS(self,doc,tag,text):
        pass

    def cardinaliteIMS(self,doc,tag,text,rcardinality='Single'):
        with tag('response_lid', rcardinality=rcardinality, ident='response_'+str(self.question.id)):
            with tag('render_choice', shuffle='No'):
                for id_a, answer in enumerate(self.answers):
                    with tag('response_label', ident='answer_'+str(self.question.id)+'_'+str(id_a)):
                        with tag('material'):
                            with tag('mattext', texttype="text/html"):
                                text(answer['answer_text'])

    def ownEDX(self,doc):
        pass

    def scriptEDX(self,doc):
        pass


class Essay(AnswerSet):
    """ Empty answer """
    def __init__(self,question):
        AnswerSet.__init__(self,question)

    def toHTML(self, doc):
        with doc.tag('textarea',name=self.question.getId(),placeholder=_('Your answer here')):
            doc.text('')

    def possiblesAnswersIMS(self,doc,tag,text):
        with doc.tag('response_str', rcardinality='Single', ident='response_'+str(self.question.id)):
            doc.stag('render_fib', rows=5, prompt='Box', fibtype="String")

    def toEDX(self):
        return AnswerSet.toEDX(self,'unlimited')

    def scriptEDX(self,doc):
        with doc.tag("script", type="loncapa/python"):
            doc.text("""
import re
def checkAnswerEssay(expect, ans):
    response = re.search('', ans)
    if response:
        return 1
    else:
        return 0
            """)
        doc.asis('<span id="'+str(self.question.id)+'"></span>')
        with doc.tag("script", type="text/javascript"):
            doc.asis("""
    /* The object here is to replace the single line input with a textarea */
    (function() {
    var elem = $("#"""+str(self.question.id)+"""")
        .closest("div.problem")
        .find(":text");
    /* There's CSS in the LMS that controls the height, so we have to override here */
    var textarea = $('<textarea style="height:150px" rows="20" cols="70"/>');
    console.log(elem);
    console.log(textarea);
    //This is just a way to do an iterator in JS
    for (attrib in {'id':null, 'name':null}) {
        textarea.attr(attrib, elem.attr(attrib));
    }
    /* copy over the submitted value */
    textarea.val(elem.val())
    elem.replaceWith(textarea);

    })();
            """)

    def ownEDX(self,doc):
        with doc.tag("customresponse", cfn="checkAnswerEssay"):
            doc.asis('<textline size="40" correct_answer="" label="Problem Text"/>')


class Description(AnswerSet):
    """ Emptyset, nothing!"""
    def __init__(self,question):
        AnswerSet.__init__(self,question)

    def toHTML(self,doc):
        return

    def toHTMLFB(self,doc):
        return


class TrueFalseSet(AnswerSet):
    """ True or False"""
    # Q: should I introduce Answer variables?
    def __init__(self,question,match):
        AnswerSet.__init__(self,question)
        self.answer = match.group('answer').startswith('T')
        self.feedbackWrong = stripMatch(match,"feedback")
        self.feedbackCorrect = stripMatch(match,"feedback2")

    def myprint(self):
        print (">TrueFalse:",self.answer,"--",self.feedbackWrong,"--",self.feedbackCorrect)

    def toHTML(self,doc):
        with doc.tag('ul'):
            with doc.tag('li'):
                doc.input(name = self.question.getId(), type = 'radio', value = True)
                doc.text(_('True'))
            with doc.tag('li'):
                doc.input(name = self.question.getId(), type = 'radio', value = False)
                doc.text(_('False'))

    def toHTMLFB(self,doc):
        with doc.tag('div', klass='answerFeedback'):
            doc.text(self.answer)
        if self.feedbackCorrect :
            with doc.tag('div', klass='correct_answer'):
                doc.asis(markupRendering(self.feedbackCorrect,self.question.markup))
        if self.feedbackWrong :
            with doc.tag('div', klass='wrong_answer'):
                doc.asis(markupRendering(self.feedbackWrong,self.question.markup))


    def ownEDX(self, doc):
        with doc.tag("multiplechoiceresponse"):
            with doc.tag("choicegroup", type="MultipleChoice"):
                if self.feedbackCorrect :
                    correct = 'true'
                    wrong = 'false'
                else :
                    correct = 'false'
                    wrong = 'true'
                with doc.tag("choice", correct=correct):
                    doc.text('Vrai')
                    if self.feedbackCorrect:
                        doc.asis("<choicehint>"+self.feedbackCorrect+"</choicehint>")
                with doc.tag("choice", correct=wrong):
                    doc.text('Faux')
                    if self.feedbackWrong:
                        doc.asis("<choicehint>"+self.feedbackWrong+"</choicehint>")


class NumericAnswerSet(AnswerSet):
    """ """
    def __init__(self,question,answers):
        AnswerSet.__init__(self,question)
        self.answers = answers

    def toHTML(self,doc):
        doc.input(name = self.question.getId(), type = 'number', step="any")

    def toHTMLFB(self,doc):
        with doc.tag('div', klass='answerFeedback'):
            with doc.tag('ul'):
                for a in self.answers:
                    if a.fraction>0:
                        aklass="right_answer"
                    else:
                        aklass="wrong_answer"
                    with doc.tag('li', klass=aklass):
                        doc.asis(a.toHTMLFB())
                        if a.feedback:
                            doc.asis(" &#8669; "+markupRendering(a.feedback,self.question.markup))

    def ownEDX(self,doc):
        #FIXME : Problème pour le multi answer NUMERIC, ne gère qu'une réponse
        correctAnswer = []
        for a in self.answers:
            if a.fraction > 0:
                correctAnswer.append(a)
        if len(correctAnswer) == 0:
            logging.warning('')
            return
        elif len(correctAnswer) == 1:
            correctAnswer[0].ownEDX(doc)


    # def scriptEDX(self,doc):
    #     with doc.tag('script', type="loncapa/python"):
    #         doc.text("computed_response = math.sqrt(math.fsum([math.pow(math.pi,2), math.pow(math.e,2)]))")



class MatchingSet(AnswerSet):
    """  a mapping (list of pairs) """
    def __init__(self,question,answers):
        AnswerSet.__init__(self,question)
        self.answers = answers
        self.possibleAnswers = [a.answer for a in self.answers]

    def checkValidity(self):
        valid = True
        for a in self.answers:
            valid = valid and a.isMatching
        return valid

    def myprint(self):
        print ("Answers :")
        for a in self.answers:
            a.myprint()
            print ('~~~~~')

    def toHTML(self,doc):
        with doc.tag('table'):
            for a in self.answers:
                with doc.tag('tr'):
                    with doc.tag('td'):
                        doc.text(a.question+" ")
                    with doc.tag('td'):
                        # should be distinct to _charset_ and isindex,...
                        n = self.question.getId() + a.question
                        with doc.tag('select', name= n):
                            random.shuffle(self.possibleAnswers)
                            for a in self.possibleAnswers:
                                with doc.tag('option'):
                                    doc.text(" "+a)

    def toHTMLFB(self,doc):
        with doc.tag('div', klass='groupedAnswerFeedback'):
            with doc.tag('ul'):
                for a in self.answers:
                    with doc.tag('li', klass="right_answer"):
                        doc.text(a.question)
                        doc.asis(" &#8669; ")
                        doc.text(a.answer)

    def ownEDX(self,doc):
        for a in self.answers:
            with doc.tag('h2'):
                doc.text(a.question+" ")
            with doc.tag('optionresponse'):
                options = '\"('
                random.shuffle(self.possibleAnswers)
                for a2 in self.possibleAnswers:
                    options += "'"+a2+"'"+','
                options += ')\"'
                doc.asis("<optioninput label=\""+a.question+"\" options="+options+"  correct=\""+a.answer+"\" ></optioninput>")



class ChoicesSet(AnswerSet):
    """ One or many choices in a list (Abstract)"""
    def __init__(self,question,answers):
        AnswerSet.__init__(self,question)
        self.answers = answers

    def myprint(self):
        print ("Answers :")
        for a in self.answers:
            a.myprint()
            print ('~~~~~')

    def listInteractions(self,doc,tag,text):
        for id_a, answer in enumerate(self.answers):
            score = 0
            if answer['is_right']:
                title = 'Correct'
                score = 100
            else:
                title = ''
                score = answer.fraction
            with tag('respcondition', title=title):
                with tag('conditionvar'):
                    with tag('varequal', respident='response_'+str(self.question.id)): # respoident is id of response_lid element
                        text('answer_'+str(self.question.id)+'_'+str(id_a))
                with tag('setvar', varname='SCORE', action='Set'):
                    text(score)
                doc.stag('displayfeedback', feedbacktype='Response', linkrefid='feedb_'+str(id_a))



class ShortSet(ChoicesSet):
    """ A single answer is expected but several solutions are possible """
    def __init__(self,question,answers):
        ChoicesSet.__init__(self,question,answers)

    def toHTML(self,doc):
        doc.input(name=self.question.getId(), type = 'text')

    def toHTMLFB(self,doc):
        with doc.tag('div', klass='groupedAnswerFeedback'):
            with doc.tag('ul'):
                for a in self.answers:
                    with doc.tag('li', klass="right_answer"):
                        doc.text(a.answer)
                        if a.feedback:
                            doc.asis(" &#8669; "+markupRendering(a.feedback,self.question.markup))

    def ownEDX(self,doc):
        pass



class SelectSet(ChoicesSet):
    """ One  choice in a list"""
    def __init__(self,question,answers):
        ChoicesSet.__init__(self,question,answers)

    def toHTML(self,doc):
        with doc.tag('div', klass='groupedAnswer'):
            with doc.tag("ul", klass='multichoice'):
                for a in self.answers:
                    with doc.tag("li"):
                        doc.input(name = "name", type = 'radio')
                        doc.text(a.answer)

    def toHTMLFB(self,doc):
        with doc.tag('div', klass='groupedAnswerFeedback'):
            with doc.tag("ul", klass='multichoice'):
                for a in self.answers:
                    if a.fraction>0:
                        aklass="right_answer"
                    else:
                        aklass="wrong_answer"
                    with doc.tag('li', klass=aklass):
                        doc.text(a.answer)
                        if a.feedback:
                            doc.asis(" &#8669; "+markupRendering(a.feedback,self.question.markup))

    def ownEDX(self,doc):
        with doc.tag("multiplechoiceresponse"):
            with doc.tag("choicegroup", type="MultipleChoice"):
                for a in self.answers:
                    if a.fraction>0:
                        korrect = 'true'
                    else :
                        korrect = 'false'
                    with doc.tag("choice", correct=korrect):
                        doc.text(a.answer)
                        if (a.feedback) and (len(a.feedback)> 1):
                            doc.asis("<choicehint>"+a.feedback+"</choicehint>")



class MultipleChoicesSet(ChoicesSet):
    """ One or more choices in a list"""
    def __init__(self,question,answers):
        ChoicesSet.__init__(self,question,answers)

    def checkValidity(self):
        """ Check validity the sum f fractions should be 100 """
        total = sum([ a.fraction for a in self.answers if a.fraction>0])
        return total >= 99 and total <= 100

    def toHTML(self,doc):
        with doc.tag('div', klass='groupedAnswer'):
            with doc.tag('ul', klass='multianswer'):
                for a in self.answers:
                    with doc.tag('li'):
                        doc.input(name = self.question.getId(), type = 'checkbox')
                        doc.text(a.answer)

    def toHTMLFB(self,doc):
        with doc.tag('div', klass='groupedAnswerFeedback'):
            with doc.tag('ul', klass='multianswer'):
                for a in self.answers:
                    if a.fraction>0:
                        aklass="right_answer"
                    else:
                        aklass="wrong_answer"
                    with doc.tag('li', klass=aklass):
                        doc.text(a.answer)
                        if  a.feedback:
                            doc.asis(" &#8669; "+markupRendering(a.feedback,self.question.markup))

    def ownEDX(self,doc):
        with doc.tag("choiceresponse", partial_credit="EDC"):
            with doc.tag("checkboxgroup"):
                for a in self.answers:
                    if a.fraction>0:
                        korrect = 'true'
                    else :
                        korrect = 'false'
                    with doc.tag("choice", correct=korrect):
                        doc.text(a.answer)
                        if (a.feedback) and (len(a.feedback)> 1):
                            with doc.tag("choicehint", selected="true"):
                                doc.text(a.answer+" : "+a.feedback)

    def cardinaliteIMS(self,doc,tag,text):
        ChoicesSet.cardinaliteIMS(doc,'Multiple')

    def listInteractions(self,doc,tag,text):
        with tag('respcondition', title="Correct", kontinue='No'):
            with tag('conditionvar'):
                with tag('and'):
                    for id_a, answer in enumerate(self.answers):
                        score = 0
                        try:
                            score = answer.fraction
                        except:
                            pass
                        if score <= 0:
                            with tag('not'):
                                with tag('varequal', case='Yes', respident='response_'+str(self.question.id)): # respoident is id of response_lid element
                                    text('answer_'+str(self.question.id)+'_'+str(id_a))
                        else:
                            with tag('varequal', case='Yes', respident='response_'+str(self.question.id)): # respoident is id of response_lid element
                                text('answer_'+str(self.question.id)+'_'+str(id_a))
            with tag('setvar', varname='SCORE', action='Set'):
                text('100')
            doc.stag('displayfeedback', feedbacktype='Response', linkrefid='general_fb')
        for id_a, answer in enumerate(self.answers):
            with tag('respcondition', kontinue='No'):
                with tag('conditionvar'):
                    with tag('varequal', respident='response_'+str(self.question.id), case="Yes"):
                        text('answer_'+str(self.question.id)+'_'+str(id_a))
                doc.stag('displayfeedback', feedbacktype='Response', linkrefid='feedb_'+str(id_a))



################# Single answer ######################
class Answer:
    """ one answer in a list"""
    pass


class NumericAnswer(Answer):
    def __init__(self,match):
        self.value = float(match.group('value'))
        if match.group('tolerance'):
            self.tolerance = float( match.group('tolerance') )
        else:
            self.tolerance = 0
    def toHTMLFB(self):
        return str(self.value)+"&#177;"+str(self.tolerance)

    def ownEDX(self, doc):
        with doc.tag('numericalresponse', answer = str(self.value)):
            if self.tolerance != 0.0:
                doc.asis("<responseparam type='tolerance' default='"+str(self.tolerance)+"' />")
            doc.asis("<formulaequationinput />")

class NumericAnswerMinMax(Answer):
    def __init__(self,match):
        self.mini = match.group('min')
        self.maxi = match.group('max')
    def toHTMLFB(self):
        return _('Between')+" "+str(self.mini)+" "+_('and')+" "+str(self.maxi)

    def ownEDX(self, doc):
        with doc.tag('numericalresponse', answer = "["+str(self.mini)+","+str(self.maxi)+"]"):
            doc.asis("<formulaequationinput />")


class AnswerInList(Answer):
    """ one answer in a list"""
    def __init__(self,match):
        if not match : return
        self.answer = match.group('answer').strip()
        self.feedback = stripMatch(match,"feedback")
        # At least one = sign => selects (radio buttons)
        self.select = match.group('sign') == "="

        # fractions
        if match.group('fraction') :
            self.fraction=float(match.group('fraction'))
        else:
            if match.group('sign') == "=":
                self.fraction = 100
            else:
                self.fraction = 0

        # matching
        match = reMatch.match(self.answer)
        self.isMatching = match != None
        if self.isMatching:
            self.answer = match.group('answer')
            self.question = match.group('question')

    def myprint(self):
        for key, val in self.__dict__.items():
            print ('>',key,':',val)


############ Questions ################

class Question:
    """ Question class.

    About rendering: It is up to you! But it mostly depends on the type of the answer set. Additionnally if it has a tail and the answerset is a ChoicesSet, it can be rendered as a "Missing word".
    """
    def __init__(self,source,full,cat):
        """ source of the question without comments and with comments"""
        self.id = uuid.uuid4()
        self.source = source
        self.full = full
        self.cat = cat
        self.valid = True
        self.tail = ''
        self.generalFeedback = ""
        self.parse(source)

    def getId(self):
        """ get Identifier for the question"""
        return 'Q'+str(id(self)) # TODO process title

    def parse(self,source):
        """ parses a question source. Comments should be removed first"""
        # split according to the answer
        match = reAnswer.match(source)
        if not match:
            # it is a description
            self.answers = Description(None)
            self.__parseHead(source)
        else:
            self.tail=stripMatch(match,'tail')
            self.__parseHead(match.group('head'))
            self.generalFeedback = stripMatch(match,'generalfeedback')
            # replace \n
            self.generalFeedback = re.sub(r'\\n','\n',self.generalFeedback)
            self.__parseAnswer(match.group('answer'))

    def __parseHead(self,head):
        # finds the title and the type of the text
        match = reTitle.match(head)
        if match:
            self.title = match.group('title').strip()
            textMarkup = match.group('text')
        else:
            self.title = head[:20] # take 20 first chars as a title
            textMarkup = head

        match = reMarkup.match(textMarkup)
        if match:
            self.markup = match.group('markup').lower()
            self.text = match.group('text').strip()
        else:
            self.markup = 'moodle'
            self.text = textMarkup.strip()
        # replace \n
        self.text = re.sub(r'\\n','\n',self.text)

    def __parseNumericText(self,text):
        # m=reAnswerNumericValue.match(text)
        # if m:
        #     a = NumericAnswer(m)
        # else:
        #     m = reAnswerNumericInterval.match(text)
        #     if m:
        #         a = NumericAnswerMinMax(m)
        #     else :
        #         self.valid = False
        #         return None
        m = reAnswerNumericInterval.match(text)
        if m :
             a = NumericAnswerMinMax(m)
        else :
            m = reAnswerNumericValue.match(text)
            if m:
                a = NumericAnswer(m)
            else :
                self.valid = False
                return None
        a.feedback = stripMatch(m,"feedback")
        return a

    def __parseNumericAnswers(self,answer):
        self.numeric = True;
        answers=[]
        for match in reAnswerMultipleChoices.finditer(answer):
            a = self.__parseNumericText(match.group('answer'))
            if not a:
                return
            # fractions
            if match.group('fraction') :
                a.fraction=float(match.group('fraction'))
            else:
                if match.group('sign') == "=":
                    a.fraction = 100
                else:
                    a.fraction = 0
            a.feedback = stripMatch(match,"feedback")
            answers.append(a)
        if len(answers) == 0:
            a = self.__parseNumericText(answer)
            if a:
                a.fraction=100
                answers.append(a)
        self.answers = NumericAnswerSet(self,answers)


    def __parseAnswer(self,answer):
        # Essay
        if answer=='':
            self.answers = Essay(self)
            return

        # True False
        match = reAnswerTrueFalse.match(answer)
        if match:
            self.answers = TrueFalseSet(self,match)
            return

        # Numeric answer
        if reAnswerNumeric.match(answer) != None:
            self.__parseNumericAnswers(answer[1:])
            return


        #  answers with choices and short answers
        answers=[]
        select = False
        short = True
        matching = True
        for match in reAnswerMultipleChoices.finditer(answer):
            a = AnswerInList(match)
            # one = sign is a select question
            if a.select: select = True
            # short answers are only = signs without fractions
            short = short and a.select and a.fraction == 100
            matching = matching and short and a.isMatching
            answers.append(a)

        if len(answers) > 0 :
            if matching:
                self.answers = MatchingSet(self,answers)
                self.valid = self.answers.checkValidity()
            elif short:
                self.answers = ShortSet(self,answers)
            elif select:
                self.answers = SelectSet(self,answers)
            else:
                self.answers = MultipleChoicesSet(self,answers)
                self.valid = self.answers.checkValidity()
        else:
            # not a valid question  ?
            logging.warning("Incorrect question "+self.full)
            self.valid = False

    def toHTML(self, doc=None,feedbacks=False):
        """ produces an HTML fragment, feedbacks controls the output of feedbacks"""
        if not self.valid: return ''
        if doc == None : doc=yattag.Doc()
        doc.asis('\n')
        doc.asis('<!-- New question -->')
        with doc.tag('form', klass='question'):
            with doc.tag('h3', klass='questiontitle'):
                doc.text(self.title)
            if (not feedbacks):
                if self.tail !='' :
                    with doc.tag('span', klass='questionTextInline'):
                        mdToHtml(self.text,doc)
                    with doc.tag('span', klass='questionAnswersInline'):
                        self.answers.toHTML(doc)
                    doc.text(' ')
                    doc.asis(markupRendering(self.tail,self.markup))
                else:
                    with doc.tag('div', klass='questiontext'):
                        mdToHtml(self.text,doc)
                    self.answers.toHTML(doc)
            if feedbacks:
                with doc.tag('div', klass='questiontext'):
                    mdToHtml(self.text,doc)
                self.answers.toHTMLFB(doc)
                if self.generalFeedback != '':
                    with doc.tag('div', klass='global_feedback'):
                        # gf = markdown.markdown(self.generalFeedback, MARKDOWN_EXT, output_format='xhtml')
                        doc.asis('<b><em>Feedback:</em></b><br/>')
                        mdToHtml(self.generalFeedback, doc)
        return doc

    def toEDX(self):
        """
        produces an XML fragment for EDX
        """
        if not self.valid :
            logging.warning (INVALID_FORMAT_QUESTION ) #
            return ''
        return self.answers.toEDX()

    def myprint(self):
        print ("=========Question=========")
        if not self.valid:
            return
        print (self.answers.__class__)
        for key, val in self.__dict__.items():
            if key in ['full','source',"answer","valid"]:
                continue
            if key == 'answers':
                self.answers.myprint()
            else:
                print (key,':',val)

def moodleRendering(src):
    """ See https://docs.moodle.org/23/en/Formatting_text#Moodle_auto-format"""
    # blank lines are new paragraphs, url are links, html is allowed
    # quick and dirty conversion (don't closed p tags...)
    src = transformSpecials(src)
    src = reURL.sub(r'<a href="\1">\1</a>', src)
    src = reNewLine.sub(r'<p>',src)
    return src

def htmlRendering(src):
    return transformSpecials(src)

def markdownRendering(src):
    return markdown.markdown(transformSpecials(src), MARKDOWN_EXT)

def markupRendering(src,markup='html'):
    m = sys.modules[__name__]
    rendering=markup+'Rendering'
    if rendering in m.__dict__ :
        return getattr(m,rendering)(src)
    else:
        logging.warning('Rendering error: unknown markup language '+markup)
        return src

def transformSpecials(src):
    return reSpecialChar.sub(r'\g<char>',src)

def parseFile(f):
    cleanedSource = fullSource = ""
    category='$course$'
    newCategory = None
    questions=[]

    for  line in f:
        if reSepQuestions.match(line):
            if newCategory:
                # the previous line was a category declaration
                category = newCategory
                newCategory = None
            else:
                if cleanedSource != "":
                    # this is the end of a question
                    questions.append(Question(cleanedSource,fullSource,category))
                cleanedSource = fullSource = ""
        else:
            # it is not a blank line : is it a category definition?
            match = reCategory.match(line)
            if match:
                newCategory = match.group('cat')
                continue

            # is it a comment ?
            if not reComment.match(line):
                cleanedSource += line
            fullSource+=line

    if cleanedSource != "":
        questions.append(Question(cleanedSource,fullSource,category))

    return questions


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Parses gift files.")
    parser.add_argument("-l", "--log", dest="logLevel", choices=['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'], help="Set the logging level", default='WARNING')
    parser.add_argument('f', help="gift file",type=argparse.FileType('r'))
    parser.add_argument('-H', '--html', help="html output",action="store_true")
    args = parser.parse_args()
    logging.basicConfig(filename='gift.log',filemode='w',level=getattr(logging, args.logLevel))

    questions = parseFile (args.f)
    args.f.close()

    for q in questions:
        if args.html:
            d= q.toHTML()
            print (d.getvalue())
            print ("<hr />")
        else:
            q.myprint()

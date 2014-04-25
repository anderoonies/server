import datetime
import os
import requests
import xml.etree.ElementTree as ET
from django.core.management.base import BaseCommand, CommandError
from server.models import *


# Get username/password from the environment
username = os.getenv('NUWS_TEST_USERNAME')
password = os.getenv('NUWS_TEST_PASSWORD')


term_template = """
<soapenv:Envelope xmlns:soapenc="http://schemas.xmlsoap.org/soap/encoding/" xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/" xmlns:wsa="http://schemas.xmlsoap.org/ws/2003/03/addressing/" xmlns:xsd="http://www.w3.org/2001/XMLSchema/" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance/">
  <soapenv:Header xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/">
    <wsse:Security soap:mustUnderstand="1" xmlns:soap="http://schemas.xmlsoap.org/wsdl/soap/" xmlns:wsse="http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-wssecurity-secext-1.0.xsd">
      <wsse:UsernameToken>
        <wsse:Username>{username}</wsse:Username>
        <wsse:Password>{password}</wsse:Password>
      </wsse:UsernameToken>
    </wsse:Security>
  </soapenv:Header>
  <soapenv:Body xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/">
    <GetCdescTerms>
      <ACAD_CAREER>{term_career}</ACAD_CAREER>
    </GetCdescTerms>
  </soapenv:Body>
</soapenv:Envelope>
"""
term_url = 'http://ses852dweb2.ci.northwestern.edu:40080/PSIGW/HttpListeningConnector'
term_career = 'UGRD' # Should have all the terms we want
term_headers = {
    'SOAPAction': 'NWCDESC_TERMSERV_OPR.v1',
}
def process_term(term):
    return {
        'term_id': int(term[0].text),
        'name': term[1].text,
        'shopping_cart_date': datetime.date(*map(int, term[2].text.split('-'))),
        'start_date': datetime.date(*map(int, term[3].text.split('-'))),
        'end_date': datetime.date(*map(int, term[4].text.split('-'))),
    }

def get_terms(doc):
    root = ET.fromstring(doc)
    return [process_term(term) for term in root[0][0]]

def update_terms():
    print 'Updating terms..'
    request_data = term_template.format(**globals())
    r = requests.post(term_url, data=request_data, headers=term_headers)
    terms = get_terms(r.text)
    for term in terms:
        term_obj, created = Term.objects.get_or_create(term_id=term['term_id'],
                                            defaults=term)
        if not created:
            # Update all fields
            for key, value in term.iteritems():
                setattr(term_obj, key, value)
    print 'Success: updated %d terms.' % len(terms)


school_template = """
<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/" xmlns:acad="http://peoplesoft.com/AcadGroupRequest">
  <soapenv:Header xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/">
    <wsse:Security soap:mustUnderstand="1" xmlns:soap="http://schemas.xmlsoap.org/wsdl/soap/" xmlns:wsse="http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-wssecurity-secext-1.0.xsd">
      <wsse:UsernameToken>
        <wsse:Username>{username}</wsse:Username>
        <wsse:Password>{password}</wsse:Password>
      </wsse:UsernameToken>
    </wsse:Security>
  </soapenv:Header>
   <soapenv:Body>
      <acad:AcadGroupRequest>
         <STRM>{term}</STRM>
      </acad:AcadGroupRequest>
   </soapenv:Body>
</soapenv:Envelope>
"""
school_url = 'http://ses852dweb2.ci.northwestern.edu:40080/PSIGW/HttpListeningConnector/NWCD_ACADGROUP_SERVICE.1.wsdl'
school_headers = {
    'SOAPAction': 'NWCD_AG_SERV_OPR.v1',
}

def process_school(school, term):
    return {
        'symbol': school[0].text,
        'name': school[3].text,
        'term': term,
    }

def get_schools(doc, term):
    root = ET.fromstring(doc)
    return [process_school(school, term) for school in root[0][0][2:]]

def update_schools():
    print 'Updating schools..'
    schools = []
    for term in Term.objects.iterator():
        request_data = school_template.format(term=term.term_id, **globals())
        r = requests.post(school_url, data=request_data, headers=school_headers)
        schools += get_schools(r.text, term)

    for school in schools:
        school_obj, created = School.objects.get_or_create(symbol=school['symbol'],
                                            defaults=school)
        if not created:
            for key, value in school.iteritems():
                setattr(school_obj, key, value)
    print 'Success: updated %d schools.' % len(schools)



subject_template = """
<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/" xmlns:sub="http://peoplesoft.com/SubjectRequest">
  <soapenv:Header xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/">
    <wsse:Security soap:mustUnderstand="1" xmlns:soap="http://schemas.xmlsoap.org/wsdl/soap/" xmlns:wsse="http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-wssecurity-secext-1.0.xsd">
      <wsse:UsernameToken>
        <wsse:Username>{username}</wsse:Username>
        <wsse:Password>{password}</wsse:Password>
      </wsse:UsernameToken>
    </wsse:Security>
  </soapenv:Header>
   <soapenv:Body>
      <sub:SubjectRequest>
         <STRM>{term}</STRM>
         <ACAD_GROUP>{school}</ACAD_GROUP>
      </sub:SubjectRequest>
   </soapenv:Body>
</soapenv:Envelope>
"""

subject_url = 'http://ses852dweb2.ci.northwestern.edu:40080/PSIGW/HttpListeningConnector/NWCD_SUBJ_SERVICE.1.wsdl'
subject_headers = {
    'SOAPAction': 'NWCD_SUBJ_SERV_OPR.v1',
}

def process_subject(subject, school, term):
    return {
        'symbol': subject[0].text,
        'name': subject[1].text,
        'school': school,
        'term': term
    }

def get_subjects(doc, school, term):
    root = ET.fromstring(doc)
    return [process_subject(subject, school, term) for subject in root[0][0][2][0]]

def update_subjects():
    print 'Updating subjects..'
    subjects = []
    for term in Term.objects.iterator():
        for school in School.objects.filter(term=term).iterator():
            request_data = subject_template.format(school=school.symbol, **globals())
            r = requests.post(subject_url, data=request_data, headers=subject_headers)
            subjects += get_subjects(r.text, school, term)

    for subject in subjects:
        subject_obj, created = Subject.objects.get_or_create(symbol=subject['symbol'],
                                            defaults=subject)
        if not created:
            for key, value in subject.iteritems():
                setattr(subject_obj, key, value)
    print 'Success: updated %d subjects.' % len(subjects)


courses_template = """
<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/" xmlns:des="http://peoplesoft.com/DescrRequest">
   <soapenv:Header xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/">
    <wsse:Security soap:mustUnderstand="1" xmlns:soap="http://schemas.xmlsoap.org/wsdl/soap/" xmlns:wsse="http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-wssecurity-secext-1.0.xsd">
      <wsse:UsernameToken>
        <wsse:Username>{username}</wsse:Username>
        <wsse:Password>{password}</wsse:Password>
      </wsse:UsernameToken>
    </wsse:Security>
  </soapenv:Header>
   <soapenv:Body>
      <des:DescrRequest>
         <STRM>{term}</STRM>
         <ACAD_GROUP>{school}</ACAD_GROUP>
         <SUBJECT>{subject}</SUBJECT>
      </des:DescrRequest>
   </soapenv:Body>
</soapenv:Envelope>
"""
courses_url = 'http://ses852dweb2.ci.northwestern.edu:40080/PSIGW/HttpListeningConnector/NWCD_DTL_SERVICE.1.wsdl'
courses_headers = {
    'SOAPAction': 'NWCD_ALLCLS_SERV_OPR.v1',
}

def fix_spaces(string):
    while '  ' in string:
        string = string.replace('  ', ' ')
    return string

def safe_get_child(elem, child_tag):
    child = elem.find('child_tag')
    if child:
        return child.text
    return None

def process_instructor(instructor, subject):
    return {
        'name': fix_spaces(safe_get_child(instructor, 'DISPLAY_NAME')),
        'bio': safe_get_child(instructor, 'DISPLAY_NAME'),
        'address': safe_get_child(instructor, 'CAMPUS_ADDR'),
        'phone': safe_get_child(instructor, 'PHONE'),
        'office_hours': safe_get_child(instructor, 'OFFICE_HOURS'),
        'subject': subject,
    }

def process_course_component(component, course_obj):
    mtg_info = safe_get_child(course, 'CLASS_MTG_INFO')
    room = mtg_info[0].text
    meeting_days, start_time, end_time = parse_meeting_days(mtg_info[1].text)
    return {
        'component': safe_get_child(component, 'COMPONENT'),
        'meeting_days': meeting_days,
        'start_time': start_time,
        'end_time': end_time,
        'section': safe_get_child(component, 'SECTION'),
        'room': room,
        'course': course_obj
    }
        
def parse_meeting_days(string):
    meeting_days, raw_times = string.split(' ', 1)
    raw_start, raw_end = raw_times.split(' - ')
    start_time = datetime.datetime.strptime(raw_start, time_format).time()
    end_time = datetime.datetime.strptime(raw_end, time_format).time()
    return (meeting_days, start_time, end_time)

time_format = '%I:%M%p'
def process_course(course, term, school, subject):
    # Create Instructor, CourseDesc, and CourseComponent models as necessary
    instr = process_instructor(course.find('INSTRUCTOR'), subject)
    instr_obj, _ = Instructor.objects.get_or_create(name=instr['name'],
                                                defaults=instr)

    course_descs = course.find('DESCRIPTION')
    overview = course_descs[2][1]
    descs = course_descs[3:]
    for desc in descs:
        if desc[1].text:
            desc_obj, _ = CourseDesc.objects.get_or_create(course=course,
                                               name=desc[0].text,
                                               defaults={'desc': desc[1].text})

    # Prepare other info from sub-objects
    mtg_info = course.find('CLASS_MTG_INFO')
    room = mtg_info[0].text
    meeting_days, start_time, end_time = parse_meeting_days(mtg_info[1].text)
    seats_str = safe_get_child(course, 'ENRL_CAP')
    class_num_str = safe_get_child(course, 'CLASS_NBR')
    course_id_str = safe_get_child(course, 'CRSE_ID')
    attrs = course.find('CLASS_ATTRIBUTES')[0].text
    attrs = course.find('ENRL_REQUIREMENT')[0].text

    return {
        'title': safe_get_child(course, 'COURSE_TITLE'),
        'term': term,
        'school': school.symbol,
        'instructor': instr_obj,
        'subject': subject.symbol,
        'catalog_num': safe_get_child(course, 'CATALOG_NBR'),
        'section': safe_get_child(course, 'SECTION'),
        'room': room,
        'meeting_days': meeting_days,
        'start_time': start_time,
        'end_time': end_time,
        'start_date': datetime.date(*safe_get_child(course, 'START_DT').split('-')),
        'end_date': datetime.date(*safe_get_child(course, 'END_DT').split('-')),
        'seats': int(seats_str) if seats_str else None,
        'overview': overview,
        'topic': None,
        'attributes': attrs,
        'requirements': reqs,
        'component': safe_get_child(course, 'SECTION'),
        'class_num': int(class_num_str) if class_num_str else None,
        'course_id': int(course_id_str) if course_id_str else None,
    }


def add_course_components(course, course_obj):
    components = course.findall('ASSOCIATED_CLASSES')
    for com_xml in components:
        com_dict = process_course_component(com_xml, course_obj)
        com_obj, _ = CourseComponent.objects.get_or_create(course=course_obj,
                                                defaults=com_dict)


def get_courses(doc, term, school, subject):
    root = ET.fromstring(doc)
    # Note, this returns tuples of the XML node and the processed object
    course_pairs = []
    for course in root[0][0][6:]:
        course_pairs.append((course, process_course(course, term, school, subject)))
    return course_pairs


def update_courses():
    print 'Updating courses..'
    courses = []
    for term in Term.objects.iterator():
        for school in School.objects.filter(term=term).iterator():
            for subject in Subject.objects.filter(term=term, school=school).iterator():
                print 'getting course', term.term_id, school.symbol, subject.symbol
                request_data = courses_template.format(term=term.term_id, 
                                                       school=school.symbol,
                                                       subject=subject.symbol,
                                                       **globals())
                r = requests.post(courses_url, data=request_data,
                                    headers=courses_headers)
                courses += get_courses(r.text, term, school, subject)

    # Create/update course objects
    for course_node, course in courses:
        course_obj, created = Course.objects.get_or_create(course_id=course['course_id'],
                                            defaults=course)
        add_course_components(course_node, course_obj)
        if not created:
            for key, value in course.iteritems():
                setattr(course_obj, key, value)
    print 'Success: updated %d courses.' % len(courses)


# The actual code to run
class Command(BaseCommand):
    args = '(none)'
    help = 'Scrapes the Course Data web services for updated info'

    def handle(self, *args, **options):
        print 'Updating/creating terms, schools, subjects, and courses...'
        update_terms()
        update_schools()
        update_subjects()
        update_courses()



# -*- coding: utf-8 -*-

import alfred
import json
import re
import subprocess
from fnmatch import fnmatch
from os import path
from time import time

def clean_ascii(s):
    return ''.join(i for i in s if ord(i)<128)

def fetch_whatis(max_age=604800):
    cache = path.join(alfred.work(volatile=True), u'whatis.1.json')
    if path.isfile(cache) and (time() - path.getmtime(cache) < max_age):
        return json.load(open(cache, 'r'))
    else:
        raw_pages = subprocess.check_output(['/usr/bin/man', '-k', '-Pcat', '.'])
        pagelist  = map(
            lambda x: map(lambda y: y.strip(), x.split(' - ', 1)),
            clean_ascii(raw_pages).splitlines()
        )
        whatis = {}
        for (pages, description) in pagelist:
            for page in pages.split(', '):
                whatis[page] = description
        json.dump(whatis, open(cache, 'w'))
        return whatis

def fetch_sections(whatis, max_age=604800):
    cache = path.join(alfred.work(volatile=True), u'sections.1.json')
    if path.isfile(cache) and (time() - path.getmtime(cache) < max_age):
        return set(json.load(open(cache, 'r')))
    else:
        sections = set([])
        pattern = re.compile(r'\(([^()]+)\)$')
        for (page, description) in whatis.iteritems():
            sre = pattern.search(page)
            if sre:
                sections.add(sre.group(1))
        json.dump(list(sections), open(cache, 'w'))
        return sections
    

def man_uri(manpage, protocol='x-man-page'):
    pattern = re.compile(r'(.*)\((.+)\)')
    sre = pattern.match(manpage)
    (title, section) = (sre.group(1), sre.group(2))
    return u'%s://%s/%s' % (protocol, section, title)

def filter_whatis_name(_filter, whatis):
    return {k: v for (k,v) in whatis.iteritems() if _filter(k)}

def filter_whatis_description(_filter, whatis):
    return {k: v for (k,v) in whatis.iteritems() if _filter(v)}

def result_list(query, whatis={}):
    results = []
    for (page, description) in whatis.iteritems():
        if fnmatch(page, '*%s*' % query):
            _uri = man_uri(page)
            results.append(alfred.Item(
                attributes = {'uid': _uri, 'arg': _uri},
                title = page,
                subtitle = description,
                icon = 'icon.png'
            ))
    return results

def complete(query):
    whatis = fetch_whatis()
    sections = fetch_sections(whatis)
        
    results = []
    
    # direct hit
    if query in whatis:
        _uri = man_uri(query)
        results.append(alfred.Item(
            attributes = {'uid': _uri, 'arg': _uri},
            title = query,
            subtitle = whatis[query],
            icon = 'icon.png'
        ))
    
    # section filtering
    elif query in sections:
        _uri = man_uri('(%s)' % query)
        results.append(alfred.Item(
            attributes = {'uid': _uri, 'arg': _uri, 'valid': 'no'},
            title = 'Open man page',
            subtitle = 'Scope restricted to section %s' % query,
            icon = 'icon.png'
        ))
    elif ' ' in query:
        (_section, _title) = query.split()
        pattern = re.compile(r'^.+\(%s\)$' % _section)
        _whatis = filter_whatis_name(pattern.match, whatis)
        results.extend(result_list(_title, _whatis))
        
    # standard filtering
    else:
        results.extend(result_list(query, whatis))
    
    # no matches
    if results == []:
        results.append(alfred.Item(
            attributes = {'uid': time(), 'valid': 'no'},
            title = '404 Page Not Found',
            subtitle = 'No matching man page was found',
            icon = 'icon.png'
        ))

    return alfred.xml(results)

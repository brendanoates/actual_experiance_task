"""Usage: actual_experiance_task.py

Arguments:

Options:
  -h --help
  --version

"""
# todo https://github.com/docopt/docopt/blob/master/examples/config_file_example.py
import json
import thread
from datetime import timedelta, datetime
import readchar

import pycurl
import urllib

# todo the config is valid json this could then be set in an external file
from docopt import docopt

json_config = '''{"login_url":"http://authenticationtest.herokuapp.com/login/",
"post_url":"http://authenticationtest.herokuapp.com/login/ajax/",
"test_url":"http://authenticationtest.herokuapp.com/login/", "username":"testuser",
             "password":"54321password12345", "polling_period": "30"}'''

default_dict = json.loads(json_config)

my_queue = []
time_data = []
goodput = []


def print_results(time_data, goodput):
    if len(time_data):
        print('\nA total of {} requests were made.'.format(len(time_data)))
        print('\nThe mean round trip time (RTT) was {} seconds'.format(sum(time_data) / float(len(time_data))))
        print('\nThe mean goodput value was {} bits/seconds'.format(sum(goodput) / float(len(goodput))))
    else:
        print('\nSorry there are no results to display')
    print('\nThe job has finished ')


def pycurl_debug(debug_type, debug_msg):
    if len(debug_msg) < 300:
        print("debug{}: {}".format(debug_type, debug_msg.strip()))


def input_thread(my_queue):
    while True:
        x = readchar.readkey()
        if x in ['q', u'\x03']:  # q or ctl c
            my_queue.append('q')
            break


def initialise(default_dict):
    p = pycurl.Curl()
    p.setopt(pycurl.FOLLOWLOCATION, 1)
    p.setopt(pycurl.COOKIEFILE, './cookie_test.txt')
    p.setopt(pycurl.COOKIEJAR, './cookie_test.txt')
    p.setopt(pycurl.HTTPGET, 1)
    p.setopt(pycurl.URL, default_dict['login_url'])
    p.setopt(pycurl.WRITEFUNCTION, lambda x: None)
    # p.setopt(pycurl.VERBOSE, True)
    # p.setopt(pycurl.DEBUGFUNCTION, pycurl_debug)
    p.perform()
    return p


def login(default_dict, pycurl_obj, csrf):
    pf = {'csrfmiddlewaretoken': csrf, 'username': default_dict['username'], 'password': default_dict['password']}
    fields = urllib.urlencode(pf)
    pycurl_obj.setopt(pycurl.HTTPHEADER, ['X-CSRFToken:{}'.format(csrf)])
    pycurl_obj.setopt(pycurl.POST, 1)
    pycurl_obj.setopt(pycurl.POSTFIELDS, fields)
    pycurl_obj.setopt(pycurl.URL, default_dict['post_url'])
    pycurl_obj.perform()
    return pycurl_obj


def test_the_network(default_dict, pycurl_obj):
    pycurl_obj.setopt(pycurl.COOKIE, '_gat=1;_next_=root')
    pycurl_obj.setopt(pycurl.URL, default_dict['test_url'])
    pycurl_obj.perform()
    '''
    The total time minus the pretransfer time will give the duration and save
    '''
    duration_value = pycurl_obj.getinfo(pycurl_obj.TOTAL_TIME) - pycurl_obj.getinfo(pycurl_obj.PRETRANSFER_TIME)
    '''
    Get the total data recieved
    '''
    data_recieved = pycurl_obj.getinfo(pycurl.SIZE_DOWNLOAD)
    '''
    Convert to bits per second and save
    '''
    goodput_value = (data_recieved * 8 / duration_value)
    return duration_value, goodput_value


def main():
    try:
        '''spawn new thread that will will allow for blocking read from stdin'''
        thread.start_new_thread(input_thread, (my_queue,))
        time_delta = timedelta(seconds=int(default_dict['polling_period']))

        next_period = datetime.now()
        '''
        the initial GET is to retrieve the csrf for login form submission
        '''
        pycurl_obj = initialise(default_dict)
        csrf = ''
        for info in pycurl_obj.getinfo(pycurl.INFO_COOKIELIST):
            if 'csrftoken' in info:
                cookies = info.split('\t')
                csrf = cookies[-1].strip()
                break

        '''
        login should now work with the extracted csrf
        '''
        login(default_dict, pycurl_obj, csrf)

        print('Job is now running press "q" or "ctl c" to terminate and view the results')
        while True:
            '''
            Check if we have received a request to terminate
            '''
            try:
                input_char = my_queue.pop()
                if input_char in ['q']:
                    break
            except IndexError:
                pass
            if datetime.now() >= next_period:
                next_period += time_delta
                duration_result, goodput_result = test_the_network(default_dict, pycurl_obj)
                time_data.append(duration_result)
                goodput.append(goodput_result)
    except KeyboardInterrupt:
        pass
    except Exception as e:
        print("\nAn exception has occured")
        # todo return e or log it
    try:
        pycurl_obj.close()
    except:
        pass
    print_results(time_data, goodput)


if __name__ == '__main__':
    arguments = docopt(__doc__, version='0.0.1')
    main()

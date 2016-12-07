#LinkTester
LinkTester help you check the unreachable links in your website, 
including the links in your site and links outside your site but referred in the webpage in the website.

requirements:
> python >= 3.3

usage:
> python link_tester.py -d [host] -n [threading number] -t [timeout seconds]

example:
> python link_tester.py -d m.sohu.com -n 100 -t 100

> python link_tester.py

result:
> [host]-error-[date].log will be generated in the same dir.
"""Build dependency-free, standalone HTML courses; preserve existing season 1/2."""
import json,re,pathlib,subprocess,os,shutil
ROOT=pathlib.Path(__file__).resolve().parent
sources=['stories-source.txt','stories-07-12.txt','stories-13-18.txt','stories-19-24.txt','stories-25-30.txt','stories-31-36.txt']
lessons=[]
for filename in sources:
    for line in (ROOT/filename).read_text().splitlines():
        if not line.strip(): continue
        if line.startswith('@'):
            s,n,title,prompt=line[1:].split('|')
            lesson={'season':int(s),'n':int(n),'title':title,'prompt':prompt,'stories':[]}
            lessons.append(lesson)
        else:
            title,th,zh,fact,ending,vocab=line.split('|')
            custom=[v.split('=',1) for v in vocab.split('~')]
            assert all(w in th for w,m in custom),(title,custom)
            assert 50<=len(zh)<=100,(title,len(zh))
            lesson['stories'].append({'title':title,'th':th.strip(),'zh':zh,'fact':fact,'ending':ending,'vocab':custom})
assert len(lessons)==36 and all(len(l['stories'])==5 for l in lessons)
allstories=[p for l in lessons for p in l['stories']]
assert len({p['th'] for p in allstories})==180
glossary=[x.split('|') for x in (ROOT/'glossary.txt').read_text().splitlines() if x.strip()]
assert all(len(x)==4 for x in glossary)
assert len({v[0] for v in glossary})==len(glossary)
node=os.environ.get('NODE') or shutil.which('node') or '/Applications/ChatGPT.app/Contents/Resources/cua_node/bin/node'
segmented=json.loads(subprocess.check_output([node,'-e',"let raw='';process.stdin.on('data',c=>raw+=c);process.stdin.on('end',()=>{let d=JSON.parse(raw),s=new Intl.Segmenter('th',{granularity:'word'});process.stdout.write(JSON.stringify(d.texts.map(t=>{let parts=[...s.segment(t)],b=new Set(parts.flatMap(x=>[x.index,x.index+x.segment.length]));return{count:parts.filter(x=>x.isWordLike).length,terms:d.terms.map((w,i)=>{let p=-1;while((p=t.indexOf(w,p+1))>=0){if(b.has(p)&&b.has(p+w.length))return i}return -1}).filter(i=>i>=0)}})))})"],input=json.dumps({'texts':[p['th'] for p in allstories],'terms':[g[0] for g in glossary]}).encode()))
counts=[s['count'] for s in segmented]
for p,c,segments in zip(allstories,counts,segmented):
    p['words']=c
    p['glossary']=segments['terms']
    assert 50<=c<=100,(p['title'],c)
for li,l in enumerate(lessons):
    for pi,p in enumerate(l['stories']):
        questions=[]
        for qi,field in enumerate(['fact','ending']):
            assert len({x[field] for x in l['stories']})==5
            # Pick three distinct in-scene distractors and rotate to avoid answer patterns.
            distractors=[i for i in range(5) if i!=pi]
            distractors.pop((li+pi+qi)%4)
            answer=(li*3+pi+qi*2)%4
            chosen=distractors[:]
            chosen.insert(answer,pi)
            options=[l['stories'][i][field] for i in chosen]
            evidence=p['th'][:160] if qi==0 else p['th'][-170:]
            questions.append({'prompt':l['prompt'] if qi==0 else '故事最后怎样解决，或出现了什么小插曲？','options':options,'answer':answer,'explanation':('关键信息：' if qi==0 else '故事结果：')+p[field]+'。对照原文：'+p['zh'],'evidence':evidence})
        p['questions']=questions
    for p in l['stories']:
        del p['fact'];del p['ending']
template=(ROOT/'story-course.template.html').read_text()
for season in (3,4):
    course={'season':season,'lessons':[l for l in lessons if l['season']==season],'glossary':glossary}
    for l in course['lessons']:del l['prompt']
    encoded=json.dumps(course,ensure_ascii=False,separators=(',',':')).replace('</','<\\/')
    html=template.replace('__SEASON__',str(season)).replace('__COURSE__',encoded)
    assert '__COURSE__' not in html
    (ROOT/f'season{season}.html').write_text(html)
    (ROOT/f'course-season{season}.json').write_text(json.dumps(course,ensure_ascii=False,indent=2))
print(json.dumps({'lessons':36,'stories':180,'questions':360,'thai_words':[min(counts),max(counts)],'glossary':len(glossary),'files':{f'season{s}.html':(ROOT/f'season{s}.html').stat().st_size for s in (3,4)}},ensure_ascii=False))

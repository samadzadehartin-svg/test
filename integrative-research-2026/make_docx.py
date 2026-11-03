"""Create reference/evidence and available open-access full-text Word documents."""
import csv,json,zipfile
from pathlib import Path
from docx import Document
from docx.shared import Pt,Inches
HEADINGS=[
'Neurotrophic signaling / neurotransmission / inflammation / cytoskeleton',
'Environmental, behavioral, hormonal, and nutritional influences',
'Shared and distinct mechanisms: depression and suicidal behavior',
'Integrative molecular / dendritic-spine / clinical model',
'Biomarkers, depression, treatment response, and suicide vulnerability',
'Translational implications in precision psychiatry'
]
def cite(r):
    return (str(r.get('authors',''))+'. '+str(r.get('title','[title not retrieved]'))+
            ' '+str(r.get('journal',''))+'. '+str(r.get('year',''))+
            ';'+str(r.get('volume',''))+':'+str(r.get('pages',''))+
            '. DOI: '+str(r.get('doi',''))+'. PMID: '+r['pmid'])
def setup(d):
    s=d.sections[0];s.top_margin=Inches(.65);s.bottom_margin=Inches(.65)
    s.left_margin=Inches(.73);s.right_margin=Inches(.73)
    d.styles['Normal'].font.size=Pt(9)
    d.styles['Normal'].font.name='Aptos'
def create(results,out):
    out=Path(out);out.mkdir(parents=True,exist_ok=True)
    evidence=Document();full=Document();setup(evidence);setup(full)
    evidence.add_heading('Integrative Mechanisms — Evidence Paragraphs',0)
    evidence.add_paragraph('FULL_TEXT = exact paragraph from article body in an official OA database. ABSTRACT_ONLY = PubMed abstract, not a full-text paragraph. NO_TEXT = text unavailable. Missing text has never been invented.')
    full.add_heading('Integrative Mechanisms — Open Access Full Text Bodies',0)
    full.add_paragraph('Contains only textual article body paragraphs made available by official Open Access APIs. PDF images, figures, and tables are excluded. Check the original article license before reuse.')
    log=[];nfull=0
    for idx,r in enumerate(results,1):
        name=r.get('title') or 'PMID '+r['pmid']
        sec=max(1,min(6,int(r.get('section') or 4)))
        evidence.add_heading(str(idx)+'. '+name,2)
        evidence.add_paragraph(cite(r))
        evidence.add_paragraph('PubMed: https://pubmed.ncbi.nlm.nih.gov/'+r['pmid']+'/ | PMCID '+r.get('pmcid','')+' | Subsection '+str(sec)+': '+HEADINGS[sec-1])
        evidence.add_paragraph('Evidence type: '+r.get('source_flag','NO_TEXT')+' | Source: '+r.get('oa_source',''))
        p=r.get('paragraph') or {}
        if p.get('text'):
            evidence.add_paragraph('Original section: '+p.get('section',''))
            evidence.add_paragraph(p['text'])
        else:evidence.add_paragraph('[No accessible evidence text was returned.]')
        if r.get('body'):
            nfull+=1;full.add_heading(str(nfull)+'. '+name,1)
            full.add_paragraph(cite(r))
            full.add_paragraph('https://pubmed.ncbi.nlm.nih.gov/'+r['pmid']+'/ | '+r.get('oa_source',''))
            previous=''
            for block in r['body']:
                heading=block.get('section') or ''
                if heading and heading!=previous:full.add_heading(heading,2);previous=heading
                full.add_paragraph(block['text'])
        log.append([r.get('rank',idx),r['pmid'],r.get('pmcid',''),r.get('source_flag',''),
                    len(r.get('body') or []),r.get('oa_source',''),name])
    evidence_file=out/'Integrative_Evidence_Paragraphs.docx'
    full_file=out/'Integrative_OA_Full_Texts.docx'
    evidence.save(evidence_file);full.save(full_file)
    stats_file=out/'Retrieval_Status.csv'
    with stats_file.open('w',encoding='utf-8-sig',newline='') as stream:
        writer=csv.writer(stream);writer.writerow(['rank','pmid','pmcid','source_type','fulltext_paragraphs','OA_source','article_title']);writer.writerows(log)
    report={'articles':len(results),'OA_fulltext_articles':nfull,
            'ABSTRACT_ONLY':sum(r.get('source_flag')=='ABSTRACT_ONLY' for r in results),
            'NO_TEXT':sum(r.get('source_flag')=='NO_TEXT' for r in results)}
    report_file=out/'Retrieval_Report.json'
    report_file.write_text(json.dumps(report,indent=2),encoding='utf8')
    archive=out/'Integrative_Word_Outputs.zip'
    with zipfile.ZipFile(archive,'w',compression=zipfile.ZIP_DEFLATED) as z:
        for f in [evidence_file,full_file,stats_file,report_file]:z.write(f,f.name)
    print('FINISHED:',json.dumps(report),'ZIP:',archive,flush=True)
    try:
        from google.colab import files
        files.download(str(archive))
    except:print('Download from Colab Files pane:',archive,flush=True)

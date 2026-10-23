"""Explicit operator retention job. Dry run unless apply=True."""
import time

def prune(db,days,apply=False):
    if not isinstance(days,int) or days<1:raise ValueError('Retenção deve ser de pelo menos 1 dia.')
    cutoff=time.time()-days*86400
    reports=db.execute('SELECT count(*) FROM reports WHERE created_at>0 AND created_at<?',(cutoff,)).fetchone()[0]
    # A conversation remains if it has a recent analysis. Its age is creation time;
    # do not prune conversations automatically: messages currently have no timestamps.
    feedback=db.execute('SELECT count(*) FROM feedback WHERE created<?',(cutoff,)).fetchone()[0]
    audits=db.execute('SELECT count(*) FROM audit WHERE created<?',(cutoff,)).fetchone()[0]
    if apply:
        db.execute('DELETE FROM reports WHERE created_at>0 AND created_at<?',(cutoff,))
        db.execute('DELETE FROM feedback WHERE created<?',(cutoff,));db.execute('DELETE FROM audit WHERE created<?',(cutoff,));db.commit()
    return {'reports':reports,'feedback':feedback,'audit':audits,'applied':apply,'conversations':'Preservadas; exclusão pelo usuário.'}

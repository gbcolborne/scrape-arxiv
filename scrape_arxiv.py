import os, argparse, datetime
from collections import defaultdict
import arxiv

"""
Get latest arXiv papers on NLP and related subjects.

"""
DATE_FORMAT = "%Y-%m-%d" # Date format
MAX_RESULTS = 300000 # API limit
MAX_PAPERS_PER_DAY = 200 # Max number of results expected per day

def format_result(r):
    """ 
    Given a result from an arxiv search, format the result for printing.

    """
    m = "# " + r.title
    m += "\n- URL: " + r.entry_id
    m += "\n- Published: " + r.published.strftime(DATE_FORMAT)
    if r.updated != r.published:
        m += " (updated " + r.updated.strftime(DATE_FORMAT) + ")"
    m += "\n- Authors: " + ", ".join(a.name for a in r.authors)
    if r.comment:
        m += "\n- Comments: " + r.comment
    if r.journal_ref:
        m += "\n- Journal: " + r.journal_ref
    if r.doi:
        # A URL for the resolved DOI to an external resource if present
        m += "\n- DOI: " + r.doi
    m += "\n- Primary category: " + r.primary_category
    m += "\n- Categories: " + ", ".join(r.categories)
        
    # Up to three URLs associated with this result (including the abs and pdf pages)
    links = [link.href for link in r.links if link.title and link.title != "pdf"]
    if len(links):
        m += "\n- Links: " + ", ".join(links)
    m += "\n- Abstract: \"" + r.summary + "\""
    return m

def main(args):
    # Check args
    assert args.nb_days > 0
    assert args.nb_days < 367
    assert not os.path.exists(args.path_output)

    # Dummy search to get timezone info
    search = arxiv.Search(
        query = "language",
        id_list = [],
        max_results = 1,
        sort_by = arxiv.SortCriterion.SubmittedDate,
        sort_order = arxiv.SortOrder.Descending
    )
    r = next(search.results())
    tzinfo = r.published.tzinfo

    # Get start date
    now = datetime.datetime.now(tzinfo)
    sd = now - datetime.timedelta(days=args.nb_days)
    start_date = datetime.datetime(sd.year, sd.month, sd.day, tzinfo=tzinfo)
    
    # Search
    print(f"\nINFO: getting papers from last {args.nb_days} days.")
    query = " OR ".join("cat:"+c for c in args.categories)
    max_results = min(MAX_PAPERS_PER_DAY * args.nb_days, MAX_RESULTS)
    sort_by = arxiv.SortCriterion.LastUpdatedDate if args.include_updates else arxiv.SortCriterion.SubmittedDate
    sort_order = arxiv.SortOrder.Descending
    search = arxiv.Search(
        query = query,
        id_list = [],
        max_results = max_results,
        sort_by = sort_by,
        sort_order = sort_order
    )

    # Fitler results by date
    fr = []
    start_passed = False
    date_to_count = defaultdict(int)    
    for r in search.results():
        d = r.updated if args.include_updates else r.published
        if d < start_date:
            start_passed = True
            break
        else:
            date_to_count[d.strftime(DATE_FORMAT)] += 1
            fr.append(r)

    # Check if we found any papers for that period
    if not len(fr):
        msg = f"WARNING: No papers found in last {args.nb_days} days."
        msg += " Consider increasing --nb_days"
        if not args.include_updates:
            msg += " or adding the flag --include_updates"
        msg += ".\n"
        print(msg)
        return
    
    # Check if we reached the start date
    if not start_passed:
        msg = f"WARNING: max_results ({max_results}) was too low to get all papers for the last {args.nb_days} days."
        if max_results < MAX_RESULTS:
            msg += f" Consider increasing MAX_PAPERS_PER_DAY ({MAX_PAPERS_PER_DAY})."
        else:
            msg += f" The API limits the number of results to {MAX_RESULTS}."
        print(msg)
    
    # Write results
    with open(args.path_output, 'w') as f:
        msg = "# Distribution of paper count by date of "
        msg += "update" if args.include_updates else "submission"
        f.write(msg + "\n")
        for i in range(args.nb_days):
            d = (start_date + datetime.timedelta(days=i)).strftime(DATE_FORMAT)
            f.write(f"- {d}: {date_to_count[d]}\n")
        f.write("\n********************\n\n")
        for r in fr:
            f.write(format_result(r) + "\n\n\n")
    print(f"INFO: Wrote {len(fr)} results in {os.path.abspath(args.path_output)}\n")
    return

if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("path_output")
    p.add_argument("--categories", "-c", nargs="+", default=["cs.CL"],
                   help="space-separated arXiv categories to query (e.g. cs.CL, cs.IR, cs.LG)")
    p.add_argument("--nb_days", "-n", type=int, default=7, help="Nb of days to go back to")
    p.add_argument("--include_updates", "-i", action="store_true",
                   help="Include papers papers that were updated (but not originally submitted) in this period")
    args = p.parse_args()
    main(args)

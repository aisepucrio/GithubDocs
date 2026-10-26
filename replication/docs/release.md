# Review and persistent release

## Current status

The offline analyses, curated data, dependency lock, reference tables and
reproduction checks are available in this package. No permanent archival deposit
has been created, no DOI has been minted, and no conference submission was changed.
The submitted PDF was not available for checking its artifact link or figure
numbering.

Code licensing is documented in the root `LICENSE`. The data license still
requires a choice from the data owners; see `../DATA_LICENSE.md`. Subject code,
documentation and third-party excerpts embedded in prompts/outputs retain their
own rights and attribution. The project's software license does not relicense
those materials. Confirm their redistribution conditions before public release.

## Review anonymity

The curated data replace human evaluator identifiers, mark synthetic evaluator
slots, remove operational trace/session/collector identifiers and mask email
addresses and local home paths. All six subject projects use stable anonymous identifiers
in filenames, metadata, prompts, outputs, annotations and figure labels. Their
submodules, identifiable example image, source filenames, repository URLs and
revision fingerprints are excluded. The private mapping stays outside the
repository. Embedded URLs and revision hashes in all exports are withheld.
Automated scans reject common API-key/private-key patterns and unexpected dataset
repository paths. The analysis and archive commands check the dataset policy.

The public development repository, existing Git history and previously published
pull-request diffs can still expose earlier identities. Updating current files
does not erase those records. Share the generated archive through an appropriate
anonymous review channel, not a link to the identified development repository or
its PR. The archive omits Git history, source commit IDs and private identity maps.
Personal names in commit trailers, notebook account metadata and citation
entries, and the titles and venues of related publications, are withheld.
Third-party names inside subject source code and deidentified free text remain
scientifically relevant; a final manual review should assess indirect
identification from content.
Never include `.env`, service-account credentials, virtual environments or private
mappings in an upload. Existing local archives produced before this anonymization
must not be used as the review artifact.

The [MSR 2027 Technical Papers policy](https://2027.msrconf.org/track/msr-2027-technical-papers)
expects code, data and reproduction instructions, a data-availability statement,
appropriate licensing and persistent preservation, subject to justified barriers.
It encourages availability during submission and points to
[anonymous.4open.science](https://anonymous.4open.science/) for best-effort
repository anonymization. A plain development-hosting URL is not persistent
archival preservation.

## Versioned archive

After committing the package, create an archive of the relevant tracked files:

```bash
python replication/scripts/build_archive.py --output /tmp/dome-replication.zip
```

The builder reads files from the selected Git commit, not from uncommitted local
state. It includes the offline package, tracked framework code, prompts, example
configuration, lockfiles and documentation. It excludes subject checkouts, local
outputs, credentials, source commit identifiers and Git history. `ARCHIVE_INFO.txt`
describes the review copy without identifying its development revision. An
accompanying `.sha256` file identifies the exact archive.

Before deposit, resolve the open data licensing choice, check third-party rights,
confirm the author-approved citation metadata and reconcile the figure mapping
with the submitted manuscript. Upload the reviewed version to Zenodo, Figshare,
OSF or an institutional archive, and retain a version-specific DOI/identifier.
Add the real identifier to the paper and repository once it exists. Do not invent
a DOI or use a placeholder link in the submitted paper.

For a data-availability statement, accurately state which code/data are deposited,
which results the commands reproduce, any access restrictions and the limitations
on exact model reexecution. Use the actual archive URL/DOI after deposit. Since
the paper deadline was 23 October 2026 AoE, coordinate any post-submission artifact
change with the track chairs rather than assuming it can be added to the review.

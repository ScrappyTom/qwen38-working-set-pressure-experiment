"""Resolve the source addresses rendered after recovery refresh and merging."""
from .feedback_session import FeedbackSession


class ReferenceSession(FeedbackSession):
    def resolve_region(self, reference):
        # Use the renderer's actual returned extent, including EOF clamping.
        # Designated selections and historical acquisitions remain in the parent.
        sources = [self.source(span) for span in self.recovery_focus]
        sources.extend(self.delivered_sources)
        for source in sources:
            region = self.region(source['path'], source['file_sha256'],
                                 source['returned_start_line'], source['returned_end_line'])
            if region['region_ref'] != reference:
                continue
            if self.candidate.file_sha256(region['path']) != region['file_sha256']:
                raise ValueError('source region is stale; obtain a current source reference')
            # Resolution does not establish delivery. The existing edit guard
            # independently validates the actual preceding input and candidate.
            return {key: region[key] for key in ('path', 'start_line', 'end_line')}
        return super().resolve_region(reference)

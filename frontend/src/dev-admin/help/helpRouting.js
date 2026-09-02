// frontend/src/dev-admin/help/helpRouting.js
// Deep links must survive a refresh on a kiosk tablet and must fail visibly when a
// guide id is wrong. The previous parser silently returned 'overview' for anything
// it did not recognise, which would have made every contextual link look broken.

const ID_RE = /^[a-z0-9][a-z0-9-]*$/;

export function parseHelpHash(hash, tabIds) {
  const raw = String(hash || '').replace(/^#/, '');
  const [head, ...rest] = raw.split('/');

  if (head === 'help') {
    const segments = rest.filter((segment) => segment !== '');
    const [guideId, anchor] = segments;
    const guideOk = guideId === undefined || ID_RE.test(guideId);
    const anchorOk = anchor === undefined || ID_RE.test(anchor);
    return {
      tab: 'help',
      guideId: guideId !== undefined && guideOk ? guideId : null,
      anchor: anchor !== undefined && anchorOk ? anchor : null,
      invalid: !guideOk || !anchorOk || segments.length > 2,
    };
  }
  if (tabIds.includes(head)) {
    return { tab: head, guideId: null, anchor: null, invalid: false };
  }
  return { tab: 'overview', guideId: null, anchor: null, invalid: false };
}

export function formatHelpHash(guideId, anchor) {
  return anchor ? `#help/${guideId}/${anchor}` : `#help/${guideId}`;
}

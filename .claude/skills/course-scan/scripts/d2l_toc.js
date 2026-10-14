// Paste into the javascript tool on any page of the signed-in Brightspace (D2L) course.
// Uses the browser's own session to read the course table of contents through the
// Brightspace API, and returns every topic flattened with its module path.
// Set ORG_UNIT to the course id (the number in /d2l/home/<id> or /d2l/le/content/<id>/...),
// or leave it null to read it from the current URL.
const ORG_UNIT = null;

const ou = ORG_UNIT ?? (location.pathname.match(/\/(?:home|le\/content|le\/lessons)\/(\d+)/) || [])[1];
if (!ou) throw new Error("Couldn't find the course id in the URL; set ORG_UNIT.");

const versions = await fetch("/d2l/api/versions/", { credentials: "include" }).then(r => r.json());
const le = versions.find(v => v.ProductCode === "le").LatestVersion;
const res = await fetch(`/d2l/api/le/${le}/${ou}/content/toc`, { credentials: "include" });
if (!res.ok) throw new Error(`TOC request failed: ${res.status} (signed in? access to this course?)`);
const toc = await res.json();

const course = await fetch(`/d2l/api/lp/1.0/courses/${ou}`, { credentials: "include" })
  .then(r => (r.ok ? r.json() : null)).catch(() => null);

const VIDEO_HINT = /zoom|record|lecture|video|panopto|kaltura|yuja|mediasite|vimeo|youtube|\.(mp4|m4v|mov|mkv|webm|m3u8)\b/i;
const topics = [];
(function walk(mods, path) {
  for (const m of mods || []) {
    const p = [...path, m.Title];
    for (const t of m.Topics || []) {
      topics.push({
        id: t.TopicId,
        module: p.join(" › "),
        title: t.Title,
        url: t.Url,
        type: t.TypeIdentifier,
        activity: t.ActivityType,
        hidden: !!t.IsHidden,
        view: `${location.origin}/d2l/le/content/${ou}/viewContent/${t.TopicId}/View`,
        likelyVideo: VIDEO_HINT.test(`${t.Title} ${t.Url}`) || /media|video|contentservice/i.test(`${t.TypeIdentifier} ${t.ActivityType}`),
      });
    }
    walk(m.Modules, p);
  }
})(toc.Modules, []);

({
  orgUnit: ou,
  course: course ? { name: course.Name, code: course.Code } : null,
  leVersion: le,
  topicCount: topics.length,
  likelyVideoCount: topics.filter(t => t.likelyVideo).length,
  topics,
});

const SCHEDULE_CSS =
	".my-schedule{--max-w:var(--page-max-width,760px);max-width:var(--max-w);margin:0 auto;padding:0 var(--padding-md) var(--padding-xl);}" +
	".my-schedule .month-head{font-size:var(--text-sm);font-weight:var(--weight-semibold);color:var(--text-muted);text-transform:uppercase;letter-spacing:0.4px;margin:var(--margin-lg) 0 var(--margin-sm);}" +
	".my-schedule .month-head:first-child{margin-top:0;}" +
	".my-schedule .sched-card{border:1px solid var(--border-color);border-radius:var(--border-radius-md);background:var(--bg-color);margin-bottom:var(--margin-sm);overflow:hidden;}" +
	".my-schedule .sched-card.is-today{border-color:var(--green-500);}" +
	".my-schedule .sched-card.is-cancelled{opacity:0.7;}" +
	".my-schedule .sched-row{display:flex;align-items:flex-start;gap:var(--padding-md);padding:var(--padding-md);cursor:pointer;}" +
	".my-schedule .sched-when{min-width:110px;}" +
	".my-schedule .sched-day{font-size:var(--text-base);font-weight:var(--weight-semibold);color:var(--heading-color);white-space:nowrap;}" +
	".my-schedule .sched-rel{font-size:var(--text-xs);color:var(--text-muted);}" +
	".my-schedule .sched-where{flex:1;min-width:0;}" +
	".my-schedule .sched-site{font-size:var(--text-base);color:var(--text-color);}" +
	".my-schedule .sched-sub{font-size:var(--text-sm);color:var(--text-muted);}" +
	".my-schedule .sched-meta{font-size:var(--text-sm);color:var(--text-muted);text-align:right;white-space:nowrap;}" +
	".my-schedule .sched-caret{color:var(--text-muted);font-size:12px;margin-top:4px;transition:transform 0.15s;}" +
	".my-schedule .sched-caret.expanded{transform:rotate(180deg);}" +
	".my-schedule .sched-detail{border-top:1px solid var(--border-color);padding:var(--padding-md);background:var(--subtle-fg);}" +
	".my-schedule .detail-line{display:flex;justify-content:space-between;gap:var(--padding-md);padding:5px 0;font-size:var(--text-sm);}" +
	".my-schedule .detail-line span:first-child{color:var(--text-muted);}" +
	".my-schedule .detail-line span:last-child{text-align:right;color:var(--text-color);}" +
	".my-schedule .detail-head{font-size:var(--text-xs);font-weight:var(--weight-semibold);color:var(--text-muted);text-transform:uppercase;letter-spacing:0.4px;margin:var(--margin-md) 0 2px;}" +
	".my-schedule .sched-badge{display:inline-block;padding:2px 8px;border-radius:var(--border-radius-full);font-size:var(--text-xs);font-weight:var(--weight-medium);white-space:nowrap;}" +
	".my-schedule .sched-badge.today{background:var(--bg-green);color:var(--text-on-green);}" +
	".my-schedule .sched-badge.cancelled{background:var(--bg-red);color:var(--text-on-red);}" +
	".my-schedule .empty-state{display:flex;flex-direction:column;align-items:center;padding:var(--padding-2xl) var(--padding-md);border:1px solid var(--border-color);border-radius:var(--border-radius-md);color:var(--text-muted);background:var(--bg-color);text-align:center;}" +
	"@media(max-width:600px){" +
	".my-schedule{padding:0 var(--padding-sm) var(--padding-lg);}" +
	".my-schedule .sched-row{flex-wrap:wrap;gap:var(--padding-sm);}" +
	".my-schedule .sched-when{min-width:100%;}" +
	".my-schedule .sched-meta{text-align:left;white-space:normal;}" +
	"}";

function formatClockTime(value) {
	if (!value) return "";
	// A Time field arrives as "9:30:00", not "09:30:00", so it cannot simply be truncated.
	const [hours, minutes] = String(value).split(":");
	const hour = parseInt(hours, 10);
	const suffix = hour < 12 ? "AM" : "PM";
	const hour12 = hour % 12 === 0 ? 12 : hour % 12;
	return hour12 + ":" + (minutes || "00").padStart(2, "0") + " " + suffix;
}

function formatTimeWindow(session) {
	if (!session.planned_start_time) return __("Time not set");
	const start = formatClockTime(session.planned_start_time);
	return session.planned_end_time ? start + " – " + formatClockTime(session.planned_end_time) : start;
}

function daysFromToday(date) {
	return moment(date).startOf("day").diff(moment().startOf("day"), "days");
}

function formatRelativeDay(date) {
	const days = daysFromToday(date);
	if (days === 0) return __("Today");
	if (days === 1) return __("Tomorrow");
	if (days < 7) return __("in {0} days", [days]);
	if (days < 14) return __("next week");
	return __("in {0} weeks", [Math.round(days / 7)]);
}

function joinParts(parts) {
	return parts.filter(Boolean).join(", ");
}

function renderDetail(session) {
	const lines = [
		[__("Site"), session.site],
		[__("Area"), session.location],
		[__("LSG"), session.lsg],
		[__("District"), joinParts([session.district, session.state])],
		[__("Nearest PHC / CHC"), session.phcchc],
		[__("Clinic"), session.clinic],
		[__("Unit"), session.unit],
		[__("Vehicle"), session.vehicle],
	]
		.filter(([, value]) => value)
		.map(
			([label, value]) =>
				'<div class="detail-line"><span>' +
				frappe.utils.escape_html(label) +
				"</span><span>" +
				frappe.utils.escape_html(value) +
				"</span></div>"
		)
		.join("");

	const team = (session.team || [])
		.map((member) => {
			const contact = member.mobile
				? '<a href="tel:' +
					encodeURIComponent(member.mobile) +
					'">' +
					frappe.utils.escape_html(member.mobile) +
					"</a>"
				: '<span style="color:var(--text-muted);">' + __("No number on record") + "</span>";
			return (
				'<div class="detail-line"><span>' +
				frappe.utils.escape_html(__(member.role)) +
				" · " +
				frappe.utils.escape_html(member.name) +
				"</span><span>" +
				contact +
				"</span></div>"
			);
		})
		.join("");

	return (
		'<div class="sched-detail" style="display:none;">' +
		lines +
		(team ? '<div class="detail-head">' + __("Team that day") + "</div>" + team : "") +
		"</div>"
	);
}

function renderCard(session) {
	const days = daysFromToday(session.date);
	const isCancelled = session.status === "Cancelled";
	const badge = isCancelled
		? '<span class="sched-badge cancelled">' + __("Cancelled — do not travel") + "</span>"
		: days === 0
			? '<span class="sched-badge today">' + __("Today") + "</span>"
			: "";

	return (
		'<div class="sched-card' +
		(isCancelled ? " is-cancelled" : days === 0 ? " is-today" : "") +
		'">' +
		'<div class="sched-row">' +
		'<div class="sched-when">' +
		'<div class="sched-day">' +
		frappe.utils.escape_html(moment(session.date).format("ddd D MMM")) +
		"</div>" +
		'<div class="sched-rel">' +
		frappe.utils.escape_html(formatRelativeDay(session.date)) +
		"</div></div>" +
		'<div class="sched-where">' +
		'<div class="sched-site">' +
		frappe.utils.escape_html(session.site || __("Site not set")) +
		" " +
		badge +
		"</div>" +
		'<div class="sched-sub">' +
		frappe.utils.escape_html(joinParts([session.lsg, session.district])) +
		"</div></div>" +
		'<div class="sched-meta">' +
		frappe.utils.escape_html(formatTimeWindow(session)) +
		(session.unit ? "<br>" + frappe.utils.escape_html(session.unit) : "") +
		"</div>" +
		'<i class="fa fa-chevron-down sched-caret"></i>' +
		"</div>" +
		renderDetail(session) +
		"</div>"
	);
}

function renderSchedule(sessions) {
	let currentMonth = null;
	return sessions
		.map((session) => {
			const month = moment(session.date).format("MMMM YYYY");
			const head =
				month === currentMonth
					? ""
					: '<div class="month-head">' + frappe.utils.escape_html(month) + "</div>";
			currentMonth = month;
			return head + renderCard(session);
		})
		.join("");
}

function renderEmpty(message) {
	return (
		'<div class="empty-state">' +
		'<i class="fa fa-calendar-o" style="font-size:32px;margin-bottom:10px;opacity:0.4;"></i>' +
		'<span style="font-size:var(--text-sm);">' +
		frappe.utils.escape_html(message || __("You have no clinic sessions scheduled.")) +
		"</span></div>"
	);
}

async function loadSchedule(page) {
	frappe.dom.freeze();
	let result;
	try {
		const response = await frappe.call({
			method: "bandhu_app.bandhu_app.page.my_schedule.my_schedule.get_my_schedule",
		});
		result = (response && response.message) || {};
	} catch (e) {
		return;
	} finally {
		frappe.dom.unfreeze();
	}

	const sessions = result.sessions || [];
	page.main.html(
		"<style>" +
			SCHEDULE_CSS +
			"</style>" +
			'<div class="my-schedule">' +
			(sessions.length ? renderSchedule(sessions) : renderEmpty(result.message)) +
			"</div>"
	);

	// page.main survives re-render, so a stale delegated handler would fire twice.
	page.main.off("click");
	page.main.on("click", ".sched-row", function () {
		$(this).siblings(".sched-detail").toggle();
		$(this).find(".sched-caret").toggleClass("expanded");
	});
	page.main.on("click", ".sched-detail a", function (e) {
		e.stopPropagation();
	});
}

frappe.pages["my-schedule"].on_page_load = function (wrapper) {
	const page = frappe.ui.make_app_page({
		parent: wrapper,
		title: __("My Schedule"),
		single_column: true,
	});

	page.set_secondary_action(__("Refresh"), () => loadSchedule(page));

	loadSchedule(page);
};

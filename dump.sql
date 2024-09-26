select json_object(
	'id', items.id,
	'b_id', events.body_id,
	'b_name', bodies.name,
	'agenda', agenda_url,
	'minutes', minutes_url,
	'insite', insite_url,
	'meeting_time', meeting_time,
	'year', strftime('%Y', meeting_time),
	'month', strftime('%m', meeting_time),
	'minutes_status', minutes_status,
	'a_num', agenda_number,
	'text', action_text,
	'title', title,
	'matter', json_object(
		'id', matter_id,
		'status', matter_status,
		'attach', json(matter_attachments),
		'type', matter_type
	)
)
from items
inner join events on events.id = items.event_id
inner join bodies on events.body_id = bodies.id;

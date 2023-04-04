legistar api notes

## `/matters`

not currently fetching directly from `/matters`
but some matter info is pulled from `/eventitems`

| key | fetched | type | example value
| "MatterId" | no | int | 1275 | 
| "MatterGuid" | no | str | "5111087D-FB2C-4FB1-9F66-7F8C3E019A64" | 
| "MatterLastModifiedUtc" | no | iso datetime | "2017-07-31T23:46:47.397" | 
| "MatterRowVersion" | no | str | "AAAAAAA49Gs=" | 
| "MatterFile" | no | str | "13-252" | 
| "MatterName" | no | str | null | 
| "MatterTitle" | no | str | "Proclamation Recognizing John M. Inks | 
| "MatterTypeId" | no | foreignkey `/mattertypes` | 51 | 
| "MatterTypeName" | no | str | "New Business" | 
| "MatterStatusId" | no | foreignkey `matterstatuses` | 74 | 
| "MatterStatusName" | no | str | "Filed" | 
| "MatterBodyId" | no | foreignkey `/bodies` | 138 | 
| "MatterBodyName" | no | str | "City Council" | 
| "MatterIntroDate" | no | iso datetime | "2013-12-17T00:00:00" | 
| "MatterAgendaDate" | no | iso datetime | "2014-01-07T00:00:00" | 
| "MatterPassedDate" | no | iso datetime | "2014-01-07T00:00:00" | 
| "MatterEnactmentDate" | no | iso datetime | null | 
| "MatterEnactmentNumber" | no | int | null | 
| "MatterRequester" | no | ? | null | 
| "MatterNotes" | no | str | null | 
| "MatterVersion" | no | str | "1" | 
| "MatterCost" | no | ? | null | 
| "MatterText1" | no | str | null | 
| "MatterText2" | no | str | "Lorrie.Brewer@mountainview.gov" | 
| "MatterText3" | no | str | null | 
| "MatterText4" | no | str | null | 
| "MatterText5" | no | str | null | 
| "MatterDate1" | no | str | null | 
| "MatterDate2" | no | str | null | 
| "MatterEXText1" | no | str | null | 
| "MatterEXText2" | no | str | null | 
| "MatterEXText3" | no | str | null | 
| "MatterEXText4" | no | str | null | 
| "MatterEXText5" | no | str | null | 
| "MatterEXText6" | no | str | null | 
| "MatterEXText7" | no | str | null | 
| "MatterEXText8" | no | str | null | 
| "MatterEXText9" | no | str | null | 
| "MatterEXText10" | no | str | null | 
| "MatterEXText11" | no | str | null | 
| "MatterEXDate1" | no | ? | null | 
| "MatterEXDate2" | no | ? | null | 
| "MatterEXDate3" | no | ? | null | 
| "MatterEXDate4" | no | ? | null | 
| "MatterEXDate5" | no | ? | null | 
| "MatterEXDate6" | no | ? | null | 
| "MatterEXDate7" | no | ? | null | 
| "MatterEXDate8" | no | ? | null | 
| "MatterEXDate9" | no | ? | null | 
| "MatterEXDate10" | no | ? | null | 
| "MatterAgiloftId" | no | ? | 0 | 
| "MatterReference" | no | ? | null | 
| "MatterRestrictViewViaWeb" | no | ? | false | 
| "MatterReports" | no | [] |

## `/events`

I was unable to get `EventItems` to expand.
They are fetched from `/events/ID/eventitems`

| key | fetched | type | example value |
| "EventId" | yes | int pk | 896 | 
| "EventGuid" | no | str | "DC62D62D-A475-472C-8309-7104666A3888" | 
| "EventLastModifiedUtc" | no | iso datetime | "2014-05-24T04:16:05.3" | 
| "EventRowVersion" | no | str | "AAAAAAAN2+o=" | 
| "EventBodyId" | yes | foreignkey `/bodies` | 138 | 
| "EventBodyName" | no | str | "City Council" | 
| "EventDate" | yes | iso datetime | "2014-01-07T00:00:00" | 
| "EventTime" | yes | str | "6:30 PM" | 
| "EventVideoStatus" | no | str | "Public" | 
| "EventAgendaStatusId" | no | int | 10 | 
| "EventAgendaStatusName" | no | str | "Final" | 
| "EventMinutesStatusId" | no | int | 10 | 
| "EventMinutesStatusName" | no | str | "Final" | 
| "EventLocation" | no | str | "Council Chambers - 500 Castro Street" | 
| "EventAgendaFile" | yes | url (pdf) | "http://legistar1.granicus.com/mountainview/meetings/2014/1/896_A_City_Council_14-01-07_Agenda_and_Notice.pdf" | 
| "EventMinutesFile" | yes | url (pdf) | "http://legistar1.granicus.com/mountainview/meetings/2014/1/896_M_City_Council_14-01-07_Meeting_Minutes.pdf" | 
| "EventAgendaLastPublishedUTC" | no | iso datetime | "2013-12-20T00:59:23.113" | 
| "EventMinutesLastPublishedUTC" | no | iso datetime | "2014-03-07T23:10:14.99" | 
| "EventComment" | no | ? | null | 
| "EventVideoPath" | no | ? | null | 
| "EventMedia" | no | str | "1537" | 
| "EventInSiteURL" | yes | url (html) | "https://mountainview.legistar.com/MeetingDetail.aspx?LEGID=896&GID=344&G=37932D0B-039B-4529-B6D8-73445A1D4799" | 
| "EventItems" | no | empty array | [] |

## `/bodies`

Fetch the key-value pair from this, reduces storage space a bit just to store ids

| key | fetched | type | example value |
| "BodyId" | yes | int pk | 138 | 
| "BodyGuid" | no | str | "126CADBD-5C20-48D6-98D4-739B3E573AC7" | 
| "BodyLastModifiedUtc" | no | iso datetime | "2014-05-24T04:16:07.03" | 
| "BodyRowVersion" | no | str | "AAAAAABSaSg=" | 
| "BodyName" | yes | str | "City Council" | 
| "BodyTypeId" | no | int | 42 | 
| "BodyTypeName" | no | str | "Primary Legislative Body" | 
| "BodyMeetFlag" | no | int | 1 | 
| "BodyActiveFlag" | no | int | 1 | 
| "BodySort" | no | int | 999 | 
| "BodyDescription" | no | str |"" | 
| "BodyContactNameId" | no | ? | null | 
| "BodyContactFullName" | no | ? | null | 
| "BodyContactPhone" | no | ? | null | 
| "BodyContactEmail" | no | ? | null | 
| "BodyUsedControlFlag" | no | ? | 0 | 
| "BodyNumberOfMembers" | no | ? | 0 | 
| "BodyUsedActingFlag" | no | ? | 0 | 
| "BodyUsedTargetFlag" | no | ? | 0 | 
| "BodyUsedSponsorFlag" | no | ? | 0 |

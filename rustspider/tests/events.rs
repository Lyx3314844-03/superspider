use rustspider::{EventBus, TOPIC_TASK_CREATED, TOPIC_TASK_RESULT};
use serde_json::json;

#[test]
fn event_bus_publishes_to_specific_and_wildcard_subscribers() {
    let bus = EventBus::default();
    let specific = bus.subscribe(TOPIC_TASK_CREATED);
    let wildcard = bus.subscribe("*");

    let event = bus.publish(TOPIC_TASK_CREATED, json!({"task_id": "job-1"}));

    assert_eq!(event.topic, TOPIC_TASK_CREATED);
    assert_eq!(
        specific.recv().expect("specific event").topic,
        TOPIC_TASK_CREATED
    );
    assert_eq!(
        wildcard.recv().expect("wildcard event").topic,
        TOPIC_TASK_CREATED
    );
    assert_eq!(bus.recent(Some(TOPIC_TASK_CREATED)).len(), 1);
}

#[test]
fn event_bus_tracks_multiple_topics_in_history() {
    let bus = EventBus::default();
    bus.publish(TOPIC_TASK_CREATED, json!({"task_id": "job-1"}));
    bus.publish(
        TOPIC_TASK_RESULT,
        json!({"task_id": "job-1", "state": "ok"}),
    );

    assert_eq!(bus.recent(None).len(), 2);
    assert_eq!(bus.recent(Some(TOPIC_TASK_RESULT)).len(), 1);
}

"use client";

import { useState } from "react";

export type PickerSlot = {
  id: number;
  start_time: string;
  end_time?: string;
};

type DateTimePickerProps = {
  value: string;
  onChange: (value: string, slotId?: string) => void;
  slots?: PickerSlot[];
  label?: string;
  triggerText?: string;
  minDate?: string;
};

function dateKey(date: Date) {
  return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, "0")}-${String(date.getDate()).padStart(2, "0")}`;
}

function localDateTime(date: Date) {
  return `${dateKey(date)}T${String(date.getHours()).padStart(2, "0")}:${String(date.getMinutes()).padStart(2, "0")}`;
}

export default function DateTimePicker({
  value,
  onChange,
  slots,
  label = "Appointment time",
  triggerText = "Choose a date and time",
  minDate,
}: DateTimePickerProps) {
  const [open, setOpen] = useState(false);
  const initialDate = value ? new Date(value) : new Date();
  const [month, setMonth] = useState(new Date(initialDate.getFullYear(), initialDate.getMonth(), 1));
  const [selectedDate, setSelectedDate] = useState(value ? dateKey(initialDate) : "");
  const activeDate = selectedDate || (value ? dateKey(new Date(value)) : "");
  const activeMonth = month;

  const minimumDate = minDate ?? dateKey(new Date());
  const slotDates = new Set((slots ?? []).map((slot) => dateKey(new Date(slot.start_time))));
  const selectedSlots = (slots ?? []).filter((slot) => dateKey(new Date(slot.start_time)) === activeDate);
  const days = Array.from({ length: 42 }, (_, index) => {
    const day = new Date(activeMonth);
    day.setDate(index - activeMonth.getDay() + 1);
    return day;
  });
  const availableTimes = Array.from({ length: 32 }, (_, index) => {
    const hour = 8 + Math.floor(index / 2);
    const minute = index % 2 ? 30 : 0;
    const date = new Date(`${activeDate}T${String(hour).padStart(2, "0")}:${String(minute).padStart(2, "0")}`);
    return date;
  }).filter((date) => dateKey(date) === activeDate && date >= new Date());

  function chooseDate(nextDate: Date) {
    const nextKey = dateKey(nextDate);
    setSelectedDate(nextKey);
    if (!value || dateKey(new Date(value)) !== nextKey) onChange("");
  }

  function chooseTime(nextValue: string, slotId?: string) {
    onChange(nextValue, slotId);
    setOpen(false);
  }

  function openPicker() {
    if (value && !selectedDate) {
      const next = new Date(value);
      setSelectedDate(dateKey(next));
      setMonth(new Date(next.getFullYear(), next.getMonth(), 1));
    }
    setOpen(true);
  }

  return (
    <>
      <button className="date-time-trigger" type="button" onClick={openPicker}>
        <span className="date-time-icon" aria-hidden="true">▦</span>
        <span>
          <small>{label}</small>
          <strong>{value ? new Date(value).toLocaleString([], { weekday: "short", month: "short", day: "numeric", hour: "numeric", minute: "2-digit" }) : triggerText}</strong>
        </span>
        <span className="date-time-arrow" aria-hidden="true">›</span>
      </button>
      {open && (
        <div className="calendar-backdrop" role="presentation" onMouseDown={(event) => { if (event.currentTarget === event.target) setOpen(false); }}>
          <div className="calendar-modal" role="dialog" aria-modal="true" aria-label="Choose date and time">
            <div className="calendar-modal-head">
              <div>
                <p className="eyebrow"><span>Schedule</span> Choose your time</p>
                <h2>When should we meet?</h2>
              </div>
              <button className="calendar-close" type="button" aria-label="Close calendar" onClick={() => setOpen(false)}>×</button>
            </div>
            <div className="calendar-month">
              <button className="calendar-nav" type="button" aria-label="Previous month" onClick={() => setMonth(new Date(activeMonth.getFullYear(), activeMonth.getMonth() - 1, 1))}>‹</button>
              <strong>{activeMonth.toLocaleString([], { month: "long", year: "numeric" })}</strong>
              <button className="calendar-nav" type="button" aria-label="Next month" onClick={() => setMonth(new Date(activeMonth.getFullYear(), activeMonth.getMonth() + 1, 1))}>›</button>
            </div>
            <div className="calendar-weekdays">{["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"].map((day) => <span key={day}>{day}</span>)}</div>
            <div className="calendar-days">
              {days.map((day) => {
                const key = dateKey(day);
                const isPast = key < minimumDate;
                const isAvailable = slots ? slotDates.has(key) : !isPast;
                return <button className={`${day.getMonth() === activeMonth.getMonth() ? "" : "muted"} ${activeDate === key ? "selected" : ""} ${isAvailable ? "has-slots" : ""}`} disabled={isPast || !isAvailable} type="button" key={key} onClick={() => chooseDate(day)}>{day.getDate()}{isAvailable && <i aria-hidden="true" />}</button>;
              })}
            </div>
            <div className="calendar-times">
              <div className="calendar-times-head"><strong>{activeDate ? new Date(`${activeDate}T12:00:00`).toLocaleDateString([], { weekday: "long", month: "long", day: "numeric" }) : "Choose a date"}</strong><span>{slots ? `${selectedSlots.length} open times` : "Choose an open time"}</span></div>
              <div className="time-options">
                {!activeDate ? <p>Choose a date to see open times.</p> : slots ? selectedSlots.length === 0 ? <p>No available slots for this date. Choose another date.</p> : selectedSlots.map((slot) => <button className={value === slot.start_time ? "selected" : ""} type="button" key={slot.id} onClick={() => chooseTime(slot.start_time, String(slot.id))}>{new Date(slot.start_time).toLocaleTimeString([], { hour: "numeric", minute: "2-digit" })}</button>) : availableTimes.map((time) => <button className={value === localDateTime(time) ? "selected" : ""} type="button" key={time.toISOString()} onClick={() => chooseTime(localDateTime(time))}>{time.toLocaleTimeString([], { hour: "numeric", minute: "2-digit" })}</button>)}
              </div>
            </div>
          </div>
        </div>
      )}
    </>
  );
}

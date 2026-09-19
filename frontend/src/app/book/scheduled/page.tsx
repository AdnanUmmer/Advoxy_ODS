import { redirect } from "next/navigation";

export default function ScheduledBookingPage() {
  redirect("/search?booking_type=SCHEDULED&when=scheduled");
}

# UI / UX improvements

## Homepage
- Search/filter dock is the primary action and stays visible in the sticky header.
- Filters can be cleared individually without losing the other choices.
- Default homepage shows only 6 curated tours; users can explicitly request all tours.
- Tour cards have stronger visual hierarchy: destination, duration/hotel metadata, services, price and one clear CTA.
- Destination browsing is grouped by continent with a lightweight horizontal mobile scroller.
- No slider, image library, animation framework or client-side state manager is required.

## Reservation
- Selected tour, services and price stay visible while entering the phone number.
- Clear 3-step progress: selection → phone → call.
- Explicit message that there is no payment and no account creation at this step.
- Success page displays a short tracking reference.

## Performance
- Homepage and reservation route remain Server Components.
- Main tour visuals are CSS gradients instead of image payloads.
- No Framer Motion, Swiper, jQuery or icon bundle.
- Native form submission and URL query filters keep client JavaScript minimal.

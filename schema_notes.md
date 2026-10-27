# Chinook Schema Notes

## Customer and sales
- Customer -> Invoice: customer_id
- Invoice -> InvoiceLine: invoice_id

## Music catalog
- Artist -> Album: artist_id
- Album -> Track: album_id
- Genre -> Track: genre_id

## Important columns
- Track.milliseconds: track duration in milliseconds
- Invoice.total: invoice total
- InvoiceLine.unit_price: price per item
- InvoiceLine.quantity: number of items purchased
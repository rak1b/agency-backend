from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone
from authentication.api.utils.jwt_utils import verify_jwt_token, generate_tokens
from authentication.models import User
from datetime import datetime, timezone as dt_timezone


class Command(BaseCommand):
    help = (
        "Verify or issue JWTs on the server.\n"
        "Examples:\n"
        "  python manage.py test_jwt --token <JWT>\n"
        "  python manage.py test_jwt --issue --user_id 1\n"
    )

    def add_arguments(self, parser):
        parser.add_argument('--token', type=str, help='JWT token to verify')
        parser.add_argument('--issue', action='store_true', help='Issue a new access/refresh pair')
        parser.add_argument('--user_id', type=int, help='User ID to include in issued token payload')

    def handle(self, *args, **options):
        server_now = timezone.now()
        self.stdout.write(self.style.NOTICE(f"[test_jwt v2] Server time: {server_now.isoformat()}"))

        token = options.get('token')
        do_issue = options.get('issue')
        user_id = options.get('user_id')

        if not token and not do_issue:
            raise CommandError('Provide --token to verify, or --issue to mint a token.')

        if do_issue:
            if not user_id:
                raise CommandError('--issue requires --user_id')
            user = User.objects.filter(id=user_id).first()
            if not user:
                raise CommandError(f'User with id {user_id} not found')
            payload = {
                'user_id': user.id,
                'user_name': user.name or '',
                'role': '3',
                'role_title': 'merchant',
            }
            access, refresh = generate_tokens(payload)
            self.stdout.write(self.style.SUCCESS('Issued tokens:'))
            self.stdout.write(f"access_token: {access}")
            self.stdout.write(f"refresh_token: {refresh}")

        if token:
            self.stdout.write(self.style.NOTICE('Verifying provided token...'))
            try:
                decoded = verify_jwt_token(token, token_type='access')
                self._print_claims(decoded)
                self.stdout.write(self.style.SUCCESS('Token is valid.'))
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'Token verification failed: {e}'))

    def _print_claims(self, claims: dict):
        for key in ['user_id', 'user_name', 'role', 'role_title', 'type']:
            if key in claims:
                self.stdout.write(f"{key}: {claims.get(key)}")

        def fmt_delta(target_dt):
            now = timezone.now()
            delta = target_dt - now
            sign = ''
            seconds = int(delta.total_seconds())
            if seconds < 0:
                seconds = -seconds
                sign = 'ago'
            else:
                sign = 'from now'
            days, rem = divmod(seconds, 86400)
            hours, rem = divmod(rem, 3600)
            minutes, _ = divmod(rem, 60)
            parts = []
            if days:
                parts.append(f"{days}d")
            if hours or days:
                parts.append(f"{hours}h")
            parts.append(f"{minutes}m")
            return f"{' '.join(parts)} {sign}"

        def fmt_ts_line(name, ts):
            try:
                utc_dt = datetime.fromtimestamp(float(ts), tz=dt_timezone.utc)
                local_dt = utc_dt.astimezone(timezone.get_current_timezone())
                rel = fmt_delta(local_dt)
                # Show human-readable first
                return (
                    f"{name}: Local={local_dt.strftime('%Y-%m-%d %H:%M:%S %Z')} | "
                    f"UTC={utc_dt.strftime('%Y-%m-%d %H:%M:%S %Z')} | {rel}"
                )
            except Exception:
                return f"{name}: {ts}"

        # Print human-readable timing info
        iat_ts = claims.get('iat')
        nbf_ts = claims.get('nbf')
        exp_ts = claims.get('exp')

        def to_dt(ts):
            return datetime.fromtimestamp(float(ts), tz=dt_timezone.utc) if ts is not None else None

        iat_utc = to_dt(iat_ts)
        nbf_utc = to_dt(nbf_ts)
        exp_utc = to_dt(exp_ts)

        tz = timezone.get_current_timezone()
        if iat_utc:
            iat_local = iat_utc.astimezone(tz)
            self.stdout.write(f"issued_at: Local={iat_local.strftime('%Y-%m-%d %H:%M:%S %Z')} | UTC={iat_utc.strftime('%Y-%m-%d %H:%M:%S %Z')}")
        if nbf_utc and (not iat_utc or nbf_utc != iat_utc):
            nbf_local = nbf_utc.astimezone(tz)
            self.stdout.write(f"not_before: Local={nbf_local.strftime('%Y-%m-%d %H:%M:%S %Z')} | UTC={nbf_utc.strftime('%Y-%m-%d %H:%M:%S %Z')}")
        if exp_utc:
            exp_local = exp_utc.astimezone(tz)
            self.stdout.write(f"expires_at: Local={exp_local.strftime('%Y-%m-%d %H:%M:%S %Z')} | UTC={exp_utc.strftime('%Y-%m-%d %H:%M:%S %Z')}")

            # Lifetime details
            now_local = timezone.now()
            remaining = exp_local - now_local
            rem_seconds = int(remaining.total_seconds())
            if rem_seconds >= 0:
                days, rem = divmod(rem_seconds, 86400)
                hours, rem = divmod(rem, 3600)
                minutes, _ = divmod(rem, 60)
                parts = []
                if days:
                    parts.append(f"{days}d")
                if hours or days:
                    parts.append(f"{hours}h")
                parts.append(f"{minutes}m")
                self.stdout.write(f"time_remaining: {' '.join(parts)}")
            else:
                self.stdout.write("time_remaining: expired")

# python manage.py test_jwt --token 'eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VyX2lkIjo0MCwidXNlcl9uYW1lIjoiQWRtaW4gVXNlciIsInJvbGUiOiIzIiwicm9sZV90aXRsZSI6Im1lcmNoYW50IiwiZXhwIjoxNzYwNjIzOTgwLCJpYXQiOjE3NjA2MjM5MjAsIm5iZiI6MTc2MDYyMzkyMCwidHlwZSI6ImFjY2VzcyJ9.BUD2d4DAg3xD8vuGk05pRLWN-EcGMirXqrmg3k9cd4LrJl8jUTTX-yMDQ1fMlBkZCRlhDTrPl9ToMgHbn3403hSDXrRD_6iMgVU5-xd3mM6Ufyj-tWYUJXgJygLFiZiVZTjVnEpqwhE7mKhnQFNn64J1BbrkiHJ-iCX9coy92xuBn69hIza1bGK7y1E2Lztk2OKPMLvfb-OSHY7dgCwkz08nl6UESDypTkxmbxI5--A_U36mvbb04Ei_f38LnpjnTuittYbrVaRnx-HL_s6MrKFxHvE6cQZ6ap3swvbDklJIHDpzC-ALloHWKBtzQKF18gA-Mg493_d0kT6Trt06PA'
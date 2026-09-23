import RadarFeed from './radar-feed';
import feed from '../public/data/feed.json';
import community from '../config/community.json';
import type { Feed } from '../lib/feed';
export default function Home() {
  return <RadarFeed feed={feed as Feed} community={community} />;
}
